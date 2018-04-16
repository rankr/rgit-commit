#rgit-commit
---
Deduplication of commits for storing repos from GitHub

usage: python main.py [option] [arg]

1. * command: python main.py -ac path_to_git_repo
* description: absorb the commits of git repo into specific directories
<br/>
2. * command: python main.py -ca
* description: clear all the commit stored
<br/>
3. * command: python main.py -rc sha1
* description: recover a commit from rgit-commit to standard output
<br/>
4. * command: python main.py -i path_to_git_repo
* description: print the size of commit objects take in one git repository
<br/>
5. * command: python main.py -ac path_to_git_repo
* description: print the size (after different methods of deduplication) of commit objects take in storage
<br/>