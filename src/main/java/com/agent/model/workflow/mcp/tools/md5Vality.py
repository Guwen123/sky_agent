from hashlib import md5
import os

class Md5Vality:
    def __init__(self):
        self.md5_obj = md5()
        self.md5_path = "./rag/md5.txt"
        if not os.path.exists(self.md5_path):
            os.makedirs(self.md5_path)

    def md5Vality(self, text: str) -> str:
        result =  self.getMd5(text)
        with open(self.md5_path, "r") as f:
            lines = f.readlines()
        if result in lines:
            print("此数据已存在rag中")
            return False
        with open(self.md5_path, "a") as f:
            f.write(result + "\n")
        rint("数据能够添加到rag中")
        return True

    def getMd5(self, text: str) -> str:
        self.md5_obj.update(text.encode('utf-8'))
        return self.md5_obj.hexdigest()