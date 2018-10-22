# file-dedupe

Find duplicate files across multiple directories. And delete them. If you want...

This is a quick script I put together to find duplicate files on my synology diskstation. It ended up saving me 20 or so gb so thought it might come in handy to someone else.

By default the script will prompt you to ask which file(s) you want to delete. You can use the `--auto` flag to automatically delete files. Combine with the `--preserve-dirs dir1 [, dir2]` flag to prevent deleting from specific directories.

To get up and running:

```
git clone git@github.com:niross/file-dedupe.git
cd file-dedupe/
virtualenv .venv --python=python3.6
source .venv/bin/activate
pip install -r requirements.txt
python --dry-run filedd.py folder1 folder2 folder3
```

Options:

`-h` Show help

`--dry-run` Run the script without actually deleting any files. Logs any changes that would be made to stdout

`--auto` Do not prompt the user, just delete all but one of the duplicate files.

`--preserve-dirs dir1 [, dir2, dir3]` Do not automatically delete files from these directories.

`--verbose` Set log level to `DEBUG`

