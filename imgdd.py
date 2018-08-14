#!/usr/bin/env python
import argparse
import filecmp
import os
from pprint import pprint

import humanize
from pathquery import pathquery


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
    args = parser.parse_args()

    # Get a list of folders
    folders = []
    for folder in args.folder:
        if os.path.exists(folder):
            folders.append(folder)
        elif os.path.exists(os.path.join(os.path.realpath(__file__), folder)):
            folders.append(os.path.join(os.path.realpath(__file__), folder))
        else:
            raise parser.error('{} is not a valid path'.format(folder))

    # Get a list of files
    files =[]
    for folder in folders:
        for path in pathquery(folder).is_not_dir():
            files.append(path)

    # Group files by size
    files_by_size = {}
    for file in files:
        size = os.path.getsize(file)
        if size not in files_by_size:
            files_by_size[size] = []
        files_by_size[size].append(file)

    # Exclude single files
    files_by_size = {k: v for k, v in files_by_size.items() if len(v) > 1}

    duplicates = []
    for files in files_by_size.values():
        matches = set()
        for i in range(len(files)):
            for j in range(i + 1, len(files)):
                if filecmp.cmp(files[i], files[j]):
                    matches.update([files[i], files[j]])
        if len(matches) > 0:
            duplicates.append(list(matches))

    total_duplicates = sum([len(v) - 1 for v in files_by_size.values()])
    total_savings = humanize.naturalsize(
        sum([k * (len(v) - 1) for k, v in files_by_size.items()])
    )

    if args.dry_run:
        print(
            '\nFound {} duplicate files\n'
            'Deleting these files would free up {} of disk space.\n'.format(
                total_duplicates,
                total_savings
            )
        )

    else:
        total_deleted = 0
        for count, paths in enumerate(duplicates):
            # input('This is a test')
            # print('The following duplicates were found....\n')

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
            while not is_valid(answer, len(paths)):
                print('\nPlease enter valid numbers separated by spaces')
                answer = [x for x in input(prompt).split(' ') if x != '']

            if len(answer) == 0:
                print('Skipping Match {}'.format(count + 1))
                continue

            to_delete = [paths[x - 1] for x in list(map(int, answer))]
            for file in to_delete:
                os.unlink(file)
                total_deleted += 1

        print('\nDeleted {} duplicate file{}\n'.format(
            total_deleted, 's' if total_deleted != 1 else ''
        ))


def is_valid(answer, file_count):
    if len(answer) == 0:
        return True

    if False in [x.isnumeric() for x in answer]:
        return False

    selections = list(map(int, answer))
    if min(selections) < 0 or max(selections) > file_count:
        return False

    return True


if __name__ == '__main__':
    main()
