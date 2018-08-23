#!/usr/bin/env python
import argparse
import filecmp
import logging
import os

import humanize
from pathquery import pathquery


log = logging.getLogger(__name__)
handler = logging.StreamHandler()
handler.setLevel(logging.ERROR)
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
log.addHandler(handler)
log.setLevel(logging.ERROR)


class ImgDD(object):
    files = []

    def __init__(self, directories: list):
        self.directories = directories
        self.files = self._build_file_list(self.directories)

    @staticmethod
    def _build_file_list(directories: list) -> list:
        files = []
        for directory in directories:
            for path in pathquery(directory).is_not_dir().is_not_symlink():
                files.append(path)
        return files

    def _group_files_by_size(self) -> dict:
        files_by_size = {}
        for file in self.files:
            size = os.path.getsize(file)
            if size not in files_by_size:
                files_by_size[size] = []
            files_by_size[size].append(file)
        return {k: v for k, v in files_by_size.items() if len(v) > 1}

    def _confirm_run(self, auto: bool, same_dir_only: bool,
                     preserve_dirs: list=None) -> bool:
        dirs = '\n\t'.join(self.directories)
        message = (
            '\nFinding duplicate files in the following directories:\n\n'
            F'\t{dirs}\n\n'
        )
        if same_dir_only:
            message += (
                'Only duplicates found in the same folder will be '
                'taken into account\n\n'
            )

        if auto:
            message += 'Duplicates will be deleted automatically\n'
            if preserve_dirs:
                message += '\nFiles found in the below directories ' \
                           'will be preserved\n\n'
                for d in preserve_dirs:
                    message += '\t{}\n'.format(d)
                message += '\n'
        else:
            message += 'You will be prompted to select which files to delete\n'

        message += '\nAre you sure you want to continue? [Y/n] '
        answer = input(message)
        while answer.lower() not in ['', 'y', 'n']:
            answer = input('\nPlease enter Y or N')

        return answer.lower() in ['', 'y']

    def run(self, dry_run: bool=False, auto: bool=False,
            same_dir_only: bool=False, preserve_dirs: list=None):
        if dry_run:
            self._dry_run(same_dir_only=same_dir_only, auto=auto,
                          preserve_dirs=preserve_dirs)
            return

        if not self._confirm_run(auto=auto, same_dir_only=same_dir_only,
                                 preserve_dirs=preserve_dirs):
            return

        if auto:
            self._auto_delete_duplicates(same_dir_only=same_dir_only,
                                         preserve_dirs=preserve_dirs)
        else:
            self._prompt_delete_duplicates(same_dir_only=same_dir_only)

    def _shallow_compare(self):
        pass

    def _group_files_by_directory(self, files):
        directories = {}
        for file in files:
            directory = os.path.dirname(file)
            if directory not in directories:
                directories[directory] = []
            directories[directory].append(file)
        return [x for x in directories.values() if len(x) > 1]

    def _find_duplicates(self, same_dir_only: bool) -> list:
        duplicates = []
        for files in self._group_files_by_size().values():
            found = []
            for i in range(len(files)):
                matches = set()
                for j in range(i + 1, len(files)):
                    if filecmp.cmp(files[i], files[j]) \
                            and files[j] not in found:
                        matches.update([files[i], files[j]])
                        found.append(files[j])
                if len(matches) > 0:
                    if same_dir_only:
                        for grouped in self._group_files_by_directory(matches):
                            duplicates.append(grouped)
                    else:
                        duplicates.append(list(matches))
        return duplicates

    def _dry_run(self, same_dir_only: bool, auto: bool, preserve_dirs: list=None):
        if auto:
            self._auto_delete_duplicates(same_dir_only, dry_run=True,
                                         preserve_dirs=preserve_dirs)
        else:
            duplicates = self._find_duplicates(same_dir_only=same_dir_only)

            if len(duplicates) == 0:
                print('No duplicate files found')
                return

            total_duplicates = 0
            total_savings = 0
            for dupes in duplicates:
                total_duplicates += (len(dupes) - 1)
                size = os.path.getsize(dupes[0])
                total_savings += size * (len(dupes) - 1)

            print(
                '\nFound {} duplicate file{}\n'
                'Deleting these duplicates will free up {} '
                'of disk space.\n'.format(
                    total_duplicates,
                    's' if total_duplicates != 1 else '',
                    humanize.naturalsize(total_savings)
                )
            )

    @staticmethod
    def _is_valid_input_choice(answer: str, file_count: int) -> bool:
        if len(answer) == 0:
            return True

        if False in [x.isnumeric() for x in answer]:
            return False

        selections = list(map(int, answer))
        if min(selections) < 0 or max(selections) > file_count:
            return False

        return True

    def _prompt_delete_duplicates(self, same_dir_only: bool):
        total_deleted = 0
        dupes = self._find_duplicates(same_dir_only=same_dir_only)
        for count, paths in enumerate(dupes):
            prompt = 'Match {}\n' \
                     '{}\n\n' \
                     'Enter the number(s) of the file(s) to be ' \
                     'deleted (separated by spaces): '.format(
                        count + 1,
                        '\n'.join([
                            '  {}. {}'.format(
                                count + 1, path
                            ) for count, path in enumerate(paths)
                        ])
                      )

            answer = [x for x in input(prompt).split(' ') if x != '']
            while not self._is_valid_input_choice(answer, len(paths)):
                print('\nPlease enter valid numbers separated by spaces')
                answer = [x for x in input(prompt).split(' ') if x != '']

            if len(answer) == 0:
                log.info('Skipping Match %s', count + 1)
                continue

            to_delete = [paths[x - 1] for x in list(map(int, answer))]
            for file in to_delete:
                log.debug('Deleting %s', str(file))
                os.unlink(file)
                total_deleted += 1

        print('\nDeleted {} duplicate file{}\n'.format(
            total_deleted, 's' if total_deleted != 1 else ''
        ))

    def _auto_delete_duplicates(self, same_dir_only: bool, dry_run: bool=False,
                                preserve_dirs: list=None):
        total_deleted = 0
        dupes = self._find_duplicates(same_dir_only=same_dir_only)
        for count, files in enumerate(dupes):
            to_delete = files
            if preserve_dirs:
                for i in reversed(range(len(to_delete))):
                    for preserve_path in preserve_dirs:
                        if to_delete[i].startswith(preserve_path):
                            if dry_run:
                                print('+ Preserving {}'.format(to_delete[i]))
                            else:
                                log.info('Preserving %s', to_delete[i])
                            to_delete.pop(i)
                            break
            for file in to_delete[1:]:
                if dry_run:
                    print('+ Keeping {}'.format(files[0]))
                    print('- Deleting : {}'.format(file))
                else:
                    log.info('Deleting duplicate %s', file)
                if not dry_run:
                    os.unlink(file)
                total_deleted += 1
            print('----')
        if dry_run:
            print('{} file{} would have been automatically deleted'.format(
                total_deleted, 's' if total_deleted != 1 else ''
            ))
        else:
            print('Deleted {} duplicate file{}'.format(
                total_deleted, 's' if total_deleted != 1 else ''
            ))


def parse_paths(paths):
    folders = []
    for folder in paths:
        if os.path.exists(folder):
            folders.append(os.path.realpath(folder))
        elif os.path.exists(os.path.join(os.path.realpath(__file__), folder)):
            folders.append(os.path.join(os.path.realpath(__file__), folder))
        else:
            raise OSError('{} is not a valid path'.format(folder))
    return folders


def main():
    parser = argparse.ArgumentParser(
        description='Find and delete duplicate files across directories'
    )
    parser.add_argument(
        'folder',
        nargs='+',
        type=str,
        help='One or more folders to scan for images'
    )
    parser.add_argument(
        '--dry-run',
        '-d',
        action='store_true',
        default=False,
        dest='dry_run',
        help='Print number of files to be deleted and approximate size saved'
    )
    parser.add_argument(
        '--auto',
        '-a',
        action='store_true',
        default=False,
        dest='auto',
        help='Automatically delete duplicates (leaving one file in place)'
    )
    parser.add_argument(
        '--same-dir-only',
        '-s',
        action='store_true',
        default=False,
        dest='same_dir_only',
        help='Only delete duplicates found in the same directory'
    )
    parser.add_argument(
        '--preserve-dirs',
        '-p',
        default=None,
        action='append',
        type=str,
        dest='preserve_dirs',
        help='Duplicates will not be automacially deleted from preserved '
             'directories (use in conjunction with --auto)'
    )
    parser.add_argument(
        '--verbose',
        '-v',
        action='store_true',
        default=False,
        dest='verbose',
        help='Set logging level to debug'
    )
    args = parser.parse_args()

    if args.verbose:
        log.setLevel(logging.DEBUG)

    # Get a list of folders
    try:
        folders = parse_paths(args.folder)
    except OSError as e:
        raise parser.error(e)

    preserve_dirs = None
    if args.preserve_dirs is not None:
        try:
            preserve_dirs = parse_paths(args.preserve_dirs)
        except OSError as e:
            raise parser.error(e)

    imgdd = ImgDD(folders)
    try:
        imgdd.run(
            dry_run=args.dry_run,
            auto=args.auto,
            same_dir_only=args.same_dir_only,
            preserve_dirs=preserve_dirs
        )
    except KeyboardInterrupt:
        print('\nYou killed it!')


if __name__ == '__main__':
    main()
