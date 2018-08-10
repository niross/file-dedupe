#!/usr/bin/env python
import argparse
import filecmp
import os
from pprint import pprint

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

    if len(duplicates) > 0:
        print('The following duplicates were found....\n')
        for count, dupe in enumerate(duplicates):
            print('** Match {} **'.format(count + 1))
            for file in dupe:
                print('  {}'.format(file))
            print('')

    else:
        print('No duplicates found')


if __name__ == '__main__':
    main()
