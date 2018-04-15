#coding: utf-8
import os
import commands
import subprocess
import zlib
from func import read_chunk_from_pack, read_number_from_file, idx_pack_from_repo
import rgit_commit_csv_store as rccs
import shutil


MSBBIT = 1<<31

class OBJECT:
	def __init__(self, type = '', \
	size_cmpr = -1, size_delta_cmpr = -1, raw_data = ''):
		self.type = type
		self.size_cmpr = size_cmpr
		self.size_delta_cmpr = size_delta_cmpr
		self.raw_data = raw_data

def objsize_from_all_pack(repo_path, type_list = ['commit', 'blob', 'tree', 'tag']):
	pairs = idx_pack_from_repo(repo_path)
	s = 0
	for i, j in pairs:
		s += objsize_from_pack(i, j, type_list = type_list)
	return s
	
def objsize_from_pack(idxPath, packPath, type_list = ['commit', 'blob', 'tag', 'tree']):
	f_idx = open(idxPath, 'rb')
	f_idx.seek(4*257)

	#I dnt know if it's little endian
	obj_num = read_number_from_file(f_idx, 4)
	obj_list = []
	sha2size = {}
	for i in xrange(0, obj_num):
		j = ""
		for k in xrange(0, 20):
			a = hex(ord(f_idx.read(1)))[2:]
			if len(a)==1:
				a = '0' + a
			j = j + a
		obj_list.append(j)

	f_idx.seek(4*258 + 24*obj_num, 0)
	#if offset is negative, then the offset is in layer5 not in layer4
	obj_offset_list = []
	layer5_list = []

	for i in xrange(0, obj_num):
		j = read_number_from_file(f_idx, 4)
		if not j&MSBBIT:
			obj_offset_list.append(j&(~MSBBIT))
			sha2size[obj_list[i]] = 4
		else:
			obj_offset_list.append(-1)
			layer5_list.append((i, j))
			sha2size[obj_list[i]] = 8

	def cmp_second(x, y):
		if x[1]>y[1]:
			return 1
		if x[1]<y[1]:
			return -1
		return 0
	layer5_list.sort(cmp_second)

	for index, offset_of_layer5 in layer5_list:
		obj_offset_list[index] = read_number_from_file(f_idx, 8, bigendian = False)

	f_idx.close()

	#now the offset of obj in packfile are well
	#I've prove the base object is before the deltaed object

	f_pack = open(packPath, 'rb')
	f_pack.seek(12, 0)
	
	obj_list = zip(obj_list, obj_offset_list)
	obj_list.sort(cmp_second)

	obj_hash = {}
	off2sha = {}
	for i, j in obj_list:
		#not need to store sha in offset
		obj_hash[i] = OBJECT()
		off2sha[j] = i

	def handle_delta(string, idx, base_obj):
		string = zlib.decompress(string[idx:])
		tail_idx = len(string)
		#read two var-len int first
		idx = 0
		i = 7
		a = ord(string[idx])
		idx += 1
		src_size = a&0x7f
		while a&0x80:
			a = ord(string[idx])
			src_size |= (a&0x7f)<<i
			i += 7
			idx += 1

		tar_size = 0
		i = 0
		while True:
			#read two var-len int first
			a = ord(string[idx])
			tar_size |= (a&0x7f)<<i
			i += 7
			idx += 1
			if not a&(0x80):
					break
		#now deal with copy and insert command
		tar_data = ''
		while idx < tail_idx:
			a = ord(string[idx])
			idx += 1
			if a&(0x80):#copy
				offset = 0
				copy_len = 0
				if a&(1):
					offset = ord(string[idx])
					idx += 1
				if a&(2):
					offset |= ord(string[idx])<<8
					idx += 1
				if a&(4):
					offset |= ord(string[idx])<<16
					idx += 1
				if a&(8):
					offset |= ord(string[idx])<<24
					idx += 1
				if a&(0x10):
					copy_len = ord(string[idx])
					idx += 1
				if a&(0x20):
					copy_len |= ord(string[idx])<<8
					idx += 1
				if a&(0x40):
					copy_len |= ord(string[idx])<<16
					idx += 1
				if copy_len==0:
					copy_len = 0x10000
				
				tar_data += base_obj.raw_data[offset : offset + copy_len]
			else:#insert
				tar_data += string[idx:idx+a]
				idx += a
			if idx > tail_idx:
				print 'error in handle_delta, idx is bigger than string:\
 idx is%d, tail_idx is %d'%(idx, tail_idx)
				exit()
		return tar_data

	ret = []
	for i in xrange(0, len(obj_list)):
		#the type of base object and deltaed object is the same
		compressed_data = ''
		if i != len(obj_list) - 1:
			read_len = obj_list[i+1][1] - obj_list[i][1]
		else:
			read_len = -1

		now_sha = obj_list[i][0]
		obj_type, to_process, obj_len = read_chunk_from_pack(f_pack, read_len)
		
		if obj_type == "ofs_delta":
			j = 1
			a = ord(to_process[0])
			base_real_offset = a&0x7f
			while a&0x80:#from the source code of git
				a = ord(to_process[j])
				base_real_offset = ((base_real_offset + 1)<<7) | (a&(0x7f))
				j += 1

			base_obj_sha1 = off2sha[obj_list[i][1] - base_real_offset]
			obj_hash[now_sha].type = obj_hash[base_obj_sha1].type
			if obj_hash[now_sha].type not in type_list:
				continue
			obj_hash[now_sha].raw_data = handle_delta(to_process, j, obj_hash[base_obj_sha1])
			obj_hash[now_sha].size_cmpr = len(zlib.compress(obj_hash[now_sha].raw_data))
			obj_hash[now_sha].size_delta_cmpr = len(to_process)
		elif obj_type == "ref_delta":
			base_obj_sha1 = ''
			for k in xrange(0, 20):
				a = hex(ord(to_process[k]))[2:]
				if len(a)==1:
					a = '0' + a
				base_obj_sha1 = base_obj_sha1 + a
			obj_hash[now_sha].type = obj_hash[base_obj_sha1].type
			if obj_hash[now_sha].type not in type_list:
				continue
			obj_hash[now_sha].raw_data = handle_delta(to_process, 20, obj_hash[base_obj_sha1])
			obj_hash[now_sha].size_cmpr = len(zlib.compress(obj_hash[now_sha].raw_data))
			obj_hash[now_sha].size_delta_cmpr = len(to_process)
		elif obj_type == "not exists":
			print ("Error in addObjFromPack, objType is not exists")
			exit()
		else:
			if obj_type not in type_list:
				continue
			obj_hash[now_sha].type = obj_type
			obj_hash[now_sha].raw_data = zlib.decompress(to_process)
			obj_hash[now_sha].size_cmpr = len(to_process)

	f_pack.close()

	total_size = 0
	for i in obj_hash:
		i = obj_hash[i]
		if i.type not in type_list:
			continue
		if i.size_delta_cmpr != -1:
			total_size += i.size_delta_cmpr
		else:
			total_size += i.size_cmpr
	return total_size
	
def test_commit():
	#arg: path of git repository
	
	return
	
	rccs.rgit_commit_csv_store(i, './commit_store/commit_test')
	rccs.rgit_commit_csv_store_cmt_dup(i, './commit_store/commit_test_cmt_dup')
	rccs.rgit_commit_csv_store_struc_dup(i, './commit_store/commit_test_struc_dup')
	rccs.rgit_commit_csv_store_developer_dup(i, './commit_store/commit_test_developer_dup')
	rccs.rgit_commit_csv_store_all_dup(i, './commit_store/commit_test_all_dup')
	
	
	#for test the result of different rccs method
	p = 'd://deduplication/data/rand_cpp_delta'
	a = [os.path.join(p, x) for x in os.listdir(p)]
	b,c,d = rccs.commit_csv_store_rate(a, 'd://deduplication/testZone/commit_test')
	
	print 'commit deduplication rate is', b*1.0/c
	print 'after my approach: %d\ngit pack file: %d\nraw object: %d\n'%(b,c,d)
	
	b,c,d = rccs.commit_csv_store_rate(a, 'd://deduplication/testZone/commit_test_all_dup')
	
	print 'commit deduplication rate is', b*1.0/c
	print 'after not any dedup approach: %d\ngit pack file: %d\nraw object: %d\n'%(b,c,d)
	
	
	b,c,d = rccs.commit_csv_store_rate(a, 'd://deduplication/testZone/commit_test_cmt_dup')
	
	print 'commit deduplication rate is', b*1.0/c
	print 'after not same commit dedup approach: %d\ngit pack file: %d\nraw object: %d\n'%(b,c,d)
	
	b,c,d = rccs.commit_csv_store_rate(a, 'd://deduplication/testZone/commit_test_struc_dup')
	
	print 'commit deduplication rate is', b*1.0/c
	print 'after not structure dedup approach: %d\ngit pack file: %d\nraw object: %d\n'%(b,c,d)
	
	
	b,c,d = rccs.commit_csv_store_rate(a, 'd://deduplication/testZone/commit_test_developer_dup')
	
	print 'commit deduplication rate is', b*1.0/c
	print 'after not developer dedup approach: %d\ngit pack file: %d\nraw object: %d\n'%(b,c,d)
	
	
	print '\nsuccess'


