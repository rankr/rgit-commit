#coding: utf-8
import os
import argparse
import sys
import test
import rgit_commit_csv_store as rccs
#from test import getidx

def initParse():

	parser = argparse.ArgumentParser()
	#absorb a raw git repository into rgit store, argu is the path
	parser.add_argument('-ac', '--absorb_commit', help = "absorb the commits of git repo into specific directories", nargs = "?")

	#recover a commit from rgit-commit to standard output
	parser.add_argument('-rc', '--recover-commit', help = 'recover a commit from rgit-commit to standard output', nargs = '?')
	
	#clear all the rgit-object-repos
	parser.add_argument('-ca', '--clear-all', help = "clear all the commit stored", action = 'store_true', default = False)
	
	#print the size (after delta in pack) of commit objects take in one repository
	parser.add_argument('-i', '--info', help = "print the size (after delta in pack) of commit objects take in one repository", nargs = '?')
	
	#print the size (after delta in pack) of commit objects take in one repository
	parser.add_argument('-css', '--commit-store-stat', help = "print the size (after different methods of deduplication) of commit objects take in storage", action = 'store_true', default = False)
	
	return parser


if __name__ == '__main__':
	#parsing the argus
	parser = initParse()
	args = parser.parse_args()

	args = vars(args)
	if args['absorb_commit']:
		rccs.rgit_commit_csv_store(os.path.abspath(args['absorb_commit']))
		rccs.rgit_commit_csv_store_all_dup(os.path.abspath(args['absorb_commit']))
		rccs.rgit_commit_csv_store_struc_dup(os.path.abspath(args['absorb_commit']))
		rccs.rgit_commit_csv_store_developer_dup(os.path.abspath(args['absorb_commit']))
		rccs.rgit_commit_csv_store_cmt_dup(os.path.abspath(args['absorb_commit']))
		exit()
	if args['recover_commit']:
		rccs.recover_commit(args['recover_commit'])
		exit()
	if args['info']:
		print "the commits of repo %s takes %d byte storage"%(os.path.abspath(args['info']), test.objsize_from_all_pack(os.path.abspath(args['info']), ['commit']))
		exit()
	if args['commit_store_stat']:
		print rccs.commit_print_stat()
		exit()
	if args['clear_all']:
		rccs.clear_all_commit()
		exit()