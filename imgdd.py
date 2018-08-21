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
        self.files = self._build_file_list(directories)

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

    def _find_duplicates(self) -> list:
        duplicates = []
        for files in self._group_files_by_size().values():
            matches = set()
            for i in range(len(files)):
                for j in range(i + 1, len(files)):
                    if filecmp.cmp(files[i], files[j]):
                        matches.update([files[i], files[j]])
            if len(matches) > 0:
                duplicates.append(list(matches))
        return duplicates

    def dry_run(self):
        duplicates = self._find_duplicates()

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
            'Deleting these duplicates will free up {} of disk space.\n'.format(
                total_duplicates,
                's' if total_duplicates != 1 else '',
                humanize.naturalsize(total_savings)
            )
        )

    @staticmethod
    def is_valid_input_choice(answer, file_count):
        if len(answer) == 0:
            return True

        if False in [x.isnumeric() for x in answer]:
            return False

        selections = list(map(int, answer))
        if min(selections) < 0 or max(selections) > file_count:
            return False

        return True

    def prompt_delete_duplicates(self):
        total_deleted = 0
        for count, paths in enumerate(self._find_duplicates()):
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
            while not self.is_valid_input_choice(answer, len(paths)):
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

    def auto_delete_duplicates(self):
        total_deleted = 0
        for count, files in enumerate(self._find_duplicates()):
            for file in files[1:]:
                log.info('Deleting duplicate %s', file)
                os.unlink(file)
                total_deleted += 1
        print('Deleted {} duplicate file{}'.format(
            total_deleted, 's' if total_deleted != 1 else ''
        ))


def main():
    parser = argparse.ArgumentParser(
        description='Blah rar and jah'
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
        dest='dry_run'
    )
    parser.add_argument(
        '--auto',
        '-a',
        action='store_true',
        default=False,
        dest='auto'
    )
    parser.add_argument(
        '--verbose',
        '-v',
        action='store_true',
        default=False,
        dest='verbose'
    )
    args = parser.parse_args()

    if args.verbose:
        log.setLevel(logging.DEBUG)

    # Get a list of folders
    folders = []
    for folder in args.folder:
        if os.path.exists(folder):
            folders.append(folder)
        elif os.path.exists(os.path.join(os.path.realpath(__file__), folder)):
            folders.append(os.path.join(os.path.realpath(__file__), folder))
        else:
            raise parser.error('{} is not a valid path'.format(folder))

    imgdd = ImgDD(folders)
    if args.dry_run:
        imgdd.dry_run()
    elif args.auto:
        imgdd.auto_delete_duplicates()
    else:
        imgdd.prompt_delete_duplicates()


if __name__ == '__main__':
    main()
