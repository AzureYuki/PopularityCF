import math
import hashlib
import random

'''
这个实现使用了 hashlib 这个哈希函数库来计算元素的哈希值，
并使用随机的桶索引和位置来插入元素。
在插入元素时，它还更新每个桶的权重，以便更准确地估计元素的重要性
这只是一个简单的实现，实际应用中可能需要进行更多的优化和调整。
例如未设置扩容
'''
class WeightedCuckooFilter:
	def __init__(self, capacity, error_rate, hash_n, exp, b):
		'''
		:param capacity: 预先估计的数量
		:param error_rate: 接受的误识别率
		:param hash_n 预设定的最大哈希函数个数
		:param exp 预设定的指纹最大长度(16进制下的长度，每1位代表4个二进制位)
		'''
		self.capacity = capacity
		self.error_rate = error_rate
		self.num_buckets = self.calculate_num_buckets()
		self.bucket_size = self.calculate_bucket_size()
		self.fingerprints = [None] * self.num_buckets * self.bucket_size#列表
		self.n = hash_n
		self.re = []
		self.ill = []
		self.exp = exp

	def calculate_num_buckets(self):#计算桶数量 例如3，也可直接使用输入设定
		return int(math.ceil(self.capacity / self.calculate_bucket_size()))

	def calculate_bucket_size(self):#计算桶尺寸 例如5，也可直接使用输入设定
		return int(math.ceil(-math.log(self.error_rate) / math.log(2)))

	def calculate_bucket_indexes(self):#产生桶位置 例如[0,0,0,0,0,1,1,1,1,1,2,2,2,2,2]
		bucket_indexes = []
		for i in range(self.num_buckets):
			for j in range(self.bucket_size):
				bucket_indexes.append(i)
		return bucket_indexes

	def hash_functions(self, element, k):#哈希函数
		# 需要按照权重分配哈希函数个数
		algorithms_available=['md5', 'sha1', 'sha224', 'sha256', 'sha384', 
		'sha512', 'blake2b', 'blake2s', 'sha3_224', 'sha3_256', 'sha3_384', 
		'sha3_512', 'shake_128', 'shake_256']#一共14个可用函数，后两个需要传入长度无法简单使用
		algorithms_unavailable=['sm3', 'sha512_224', 'md5-sha1', 
		'md4', 'sha512_256', 'whirlpool', 'ripemd160', 'mdc2']#这部分非所有平台支持或需要导入其他库
		return eval('hashlib.'+algorithms_available[k]+'(element.encode())')

	def get_fingerprint(self, element):#计算指纹哈希
		md5 = hashlib.md5(element.encode())
		hash_val = md5.hexdigest()
		return hash_val[0:self.exp]

	def hot_index(self,hot):#计算热度指数
		hot_index,hot_val = 1,hot
		while hot_val > 1:#指纹的热度位移值
			hot_val = hot_val//2
			hot_index +=1
		return hot_index

	def add(self, element, hot, add_num=1):#直接增加操作，元素，热度，增加数
		if hot<0: #or hot>2**self.n-1:#热度值非法
			print("热度值不合法！应当为非负数")
			self.ill.append((element, hot))
			return False
		hot_index = min(self.hot_index(hot),self.n)#元素热度指数和过滤器热度指数（支持分配的上限）中较小的那个
		fingerprint = self.get_fingerprint(element)#计算元素的指纹
		#选择哈希函数，再根据哈希函数计算值选择桶
		#hash_lib：所有可能的桶
		hash_lib = []
		for i in range(hot_index):
			hash_lib.append(int(self.hash_functions(fingerprint, i).hexdigest(),16)%2**self.n)
		#遍历所有对应桶
		for k in range(add_num-1, hot_index):
			bucket_index = hash_lib[k]
			for i in range(self.bucket_size):
				if self.fingerprints[bucket_index * self.bucket_size + i] is None:#查询该桶的所有条目是否有空
					self.fingerprints[bucket_index * self.bucket_size + i] = (fingerprint, hot, k+1)#空位存入指纹，热度值,操作序号
					return True
		#已经达到最大上限，条目都满了，需要选一个踢出
		bucket_index = hash_lib[random.randint(0, hot_index-1)]#随机取一个桶
		random_index = random.randint(0, self.bucket_size-1)#随机取一个条目
		try:
			fingerprint_old = self.fingerprints[bucket_index * self.bucket_size + random_index]#条目中存储的旧指纹
			if random.randint(1,fingerprint_old[1]+hot+2)<=hot+1:#新指纹竞争获胜
				self.fingerprints[bucket_index * self.bucket_size + random_index] = (fingerprint, hot, add_num)#踢出旧指纹并存入新指纹
				#旧指纹重新执行插入
				n,m=1,fingerprint_old[1]#求取旧指纹的热度指数和插入次数
				while m > 1:
					m = m//2
					n+=1
				if n>fingerprint_old[2]:#插入次数小于热度指数
					#print('踢出重放')
					self.add(fingerprint_old[0], fingerprint_old[1], fingerprint_old[2]+1)#踢出的元素重新计算替代位置
					return True
				else:
					self.add(fingerprint_old[0], fingerprint_old[1],1)#重置插入次数
					return True
			else:
				self.re.append((fingerprint, hot, add_num))#新指纹竞争失败，插入失败，放入保留列表
				return False
		except:
			print("insert fail")

	def reload(self, fingerprint, hot, add_num=1):#增加操作
		hot_fin,hot_val = 1,hot
		while hot_val > 1:#新指纹的热度指数和插入次数
			hot_val = hot_val//2
			hot_fin +=1
		hot_fin = min(hot_fin,self.n)#元素热度指数和过滤器热度指数（支持分配上限）中较小的那个
		#用add_num选择哈希函数，再根据哈希函数计算值选择桶
		hash_lib = []
		for i in range(hot_fin):
			hash_lib.append(int(self.hash_functions(fingerprint, i).hexdigest(),16)%2**self.n)
		#遍历还未查看的对应桶
		for k in range(add_num-1, hot_fin):
			bucket_index = int(self.hash_functions(fingerprint, k).hexdigest(),16)%2**self.n
			for i in range(self.bucket_size):
				if self.fingerprints[bucket_index * self.bucket_size + i] is None:#查询该桶的所有条目是否有空
					self.fingerprints[bucket_index * self.bucket_size + i] = (fingerprint, hot, k+1)#空位存入指纹，热度值,操作序号
					return True
		#已经达到最大上限，条目都满了，需要选一个踢出
		bucket_index = hash_lib[random.randint(0, hot_fin-1)]#随机取一个桶
		random_index = random.randint(0, self.bucket_size - 1)#随机取一个条目
		fingerprint_old = self.fingerprints[bucket_index * self.bucket_size + random_index]#条目中存储的旧指纹
		if random.randint(1,fingerprint_old[1]+hot+2)<=hot+1:#新指纹竞争获胜
			self.fingerprints[bucket_index * self.bucket_size + random_index] = (fingerprint, hot, add_num)#踢出旧指纹并存入新指纹
			#旧指纹重新执行插入
			n,m=1,fingerprint_old[1]#求取旧指纹的热度指数和插入次数
			while m > 1:
				m = m//2
				n+=1
			if n>fingerprint_old[2]:#插入次数小于热度指数
				#print('踢出重放')
				self.reload(fingerprint_old[0], fingerprint_old[1], fingerprint_old[2]+1)#踢出的元素重新计算替代位置
				return True
			else:
				self.reload(fingerprint_old[0], fingerprint_old[1],1)#重置插入次数
				return True
		else:
			self.re.append((fingerprint, hot, add_num))#新指纹竞争失败，插入失败，放入保留列表
			return False

	def lookup(self, element, hot):#查找
		fingerprint = self.get_fingerprint(element)#计算元素指纹
		hot_fin,hot_val = 1,hot
		while hot_val > 1:#新指纹的热度指数和插入次数
			hot_val = hot_val//2
			hot_fin +=1
		hot_fin = min(hot_fin,self.n)
		hash_lib = []
		#该元素对应的所有哈希函数的计算值
		for i in range(hot_fin):
			hash_lib.append(int(self.hash_functions(fingerprint, i).hexdigest(),16)%2**self.n)
		#遍历所有的对应桶
		for i in hash_lib:
			for j in range(self.bucket_size):
				if self.fingerprints[i*self.bucket_size+j]!=None:
					if self.fingerprints[i*self.bucket_size+j][0] == fingerprint and self.fingerprints[i*self.bucket_size+j][1] == hot:
						return True
		return False

	def remove(self, element,hot):#移除
		fingerprint = self.get_fingerprint(element)#计算元素指纹
		hot_fin,hot_val = 1,hot
		while hot_val > 1:#新指纹的热度指数和插入次数
			hot_val = hot_val//2
			hot_fin +=1
		hot_fin = min(hot_fin,self.n)
		hash_lib = []
		#该元素对应的所有哈希函数的计算值
		for i in range(hot_fin):
			hash_lib.append(int(self.hash_functions(fingerprint, i).hexdigest(),16)%2**self.n)
		#遍历所有的对应桶
		for i in hash_lib:
			for j in range(self.bucket_size):
				if self.fingerprints[i*self.bucket_size+j]!=None:
					if self.fingerprints[i*self.bucket_size+j][0] == fingerprint and self.fingerprints[i*self.bucket_size+j][1] == hot:
						self.fingerprints[i*self.bucket_size+j]=None
						return True
		return False

	def calculate_number(self):
		f = 0
		for i in self.fingerprints:
			f += bool(i)*1
		return f

	def calculate_hot(self):
		hot_in,hot_out = 0,0
		num_in = self.calculate_number()
		num_out = len(self.re)
		for i in self.fingerprints:
			if i!= None:
				hot_in += i[1]
		for i in self.re:
			hot_out +=i[1]
		hot_avarge = (hot_in + hot_out) / (num_in + num_out)
		hot_in = hot_in / num_in
		hot_out = hot_out / num_out
		return [hot_avarge,hot_in,hot_out]


A = WeightedCuckooFilter(100, 0.1, 4, 4, 4)#最多支持四个哈希函数，热度为0~15
print("桶的个数是：",A.num_buckets,"桶的深度是",A.bucket_size)
print("获取key-7哈希",A.hash_functions("key",7))
print("获取example-13哈希",A.hash_functions("example",13))
print("插入key-7：",A.add("key",7))
print("插入abs-16：",A.add("abs",16))
#print("打印A的所有桶和条目",A.fingerprints)
print("插入example-13：",A.add("example",13))
#print("打印A的所有桶和条目",A.fingerprints)
print("查找example-13：",A.lookup("example",13))
print("删除example-13",A.remove("example",13))
print("查找example-13：",A.lookup("example",13))
print("查找key-7：",A.lookup("key",7))
print("删除key-7",A.remove("key",7))
print("查找key-7：",A.lookup("key",7))
#print(A.fingerprints)


'''
插入元素数量：全集
成功数量：执行插入操作成功
失败：执行插入操作失败
竞争失败：包含执行插入操作失败和被挤出（溢出）的元素
非法热度：插入检查时发现热度是非法的
过滤器中元素：最后留下来的
溢出率：指原本执行插入成功，后被新元素挤出的部分
'''
