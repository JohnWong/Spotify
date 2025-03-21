from sae.storage import Bucket
import __builtin__

# patch open function
class FileResult:
    bucket = None
    mode = ''
    filename = ''
    log = ''

    def __init__(self, filename, mode):
        self.bucket = Bucket("spotify")
        self.filename = filename

    def read(self):
        return self.bucket.get_object_contents(self.filename)
    
    def write(self, data):
        self.bucket.put_object(self.filename, data)

    def seek(self, offset):
        pass
    
    def close(self):
        pass
    
    def __enter__(self, *args):
        if self.mode == 'a+':
            try:
                self.bucket.stat_object(self.filename)
            except:
                self.bucket.put_object(self.filename, "")
        return self

    def __exit__(self, *args):
        pass

_real_open = __builtin__.open

def fake_open(filename, mode='r', buffering=-1):
    if filename == "refresh_token.txt" or filename == "api.json":
        r = FileResult(filename, mode)
        return r

    return _real_open(filename, mode, buffering)

__builtin__.open = fake_open
