import os
from typing import *
import base64
import hashlib
from Crypto import Random
from Crypto.Cipher import AES
from eth_account.account import Account
from eth_account.hdaccount import ETHEREUM_DEFAULT_PATH, key_from_seed, seed_from_mnemonic
from eth_account.messages import SignableMessage, encode_defunct
from eth_utils.curried import combomethod,keccak,text_if_str,to_bytes
from eth_keys import keys
import commune as c # import commune

class Key(Account):
    crypto_type = 'eth'
    key_storage_path = os.path.expanduser('~/.eth/key')

    def __init__(self, private_key: str = None, name=None) -> None:
        self.set_private_key(private_key)
        self.name = name

    def set_key(self, key):
        key = self.get_key(key)            
        self.set_private_key(key.private_key)
        return key

    def set_private_key(self, private_key=None):
        private_key = private_key or self.create_private_key()
        if self.key_exists(private_key):
            self.load_key(private_key)
        else:
            self.private_key =  private_key or  self.create_private_key()

    def resolve_message(self, message) :
        message = c.python2str(message)
        if isinstance(message, str):
            message = encode_defunct(text=message)
        assert isinstance(message, SignableMessage)
        return message
    
    def is_valid_private_key(self, private_key):
        try:
            key = keys.PrivateKey(private_key)
            return True
        except:
            return False
    
    @property
    def private_key_string(self) -> str:
        private_key = self._private_key.hex() 
        private_key = '0x' + private_key if not private_key.startswith('0x') else private_key
        return private_key

    @property
    def private_key(self) -> bytes:
        return self._private_key
    
    @private_key.setter
    def private_key(self, private_key:str):
        if isinstance(private_key, str):
            if private_key.startswith('0x'):
                private_key = private_key[2:]
            private_key = bytes.fromhex(private_key)
        self._private_key = private_key
        return private_key
    
    def resolve_key(self, key):
        if isinstance(key, str):
            key = self.get_key(key)
        else:
            key = key or self
        assert isinstance(key, Key), f'Invalid key {key}'
        return key
                    
    def sign(self, message: Union[SignableMessage,str, dict], key=None) -> Dict:
        key = self.resolve_key(key)
        signable_message = self.resolve_message(message)
        signed_msg =  Account.sign_message(signable_message, self.private_key)
        return {
            'message': signed_msg.message_hash.hex(),
            'signature': signed_msg.signature.hex(),
            'vrs': [signed_msg.v, signed_msg.r, signed_msg.s],
            'address': self.address
        }


    @property
    def public_key(self) -> str:
        return self.private_key_to_public_key(self.private_key)
    
    @property
    def address(self):
        return self.public_key_to_address(self.public_key.to_hex())
    
    @classmethod
    def address_to_public_key(cls, address:str) -> str:
        '''
        Convert address to public key
        '''
        if address.startswith('0x'):
            address = address[2:]
        address = bytes.fromhex(address)
        return address.hex()
        
    def public_key_to_address(self, public_key: str) -> str:
        '''
        Convert public key to address
        '''
        if public_key.startswith('0x'):
            public_key = public_key[2:]
        public_key = bytes.fromhex(public_key)
        return keys.PublicKey(public_key).to_checksum_address()
    
    @staticmethod
    def private_key_to_public_key(private_key: str) -> str:
        '''
        Conert private key to public key
        '''
        private_key_object = keys.PrivateKey(private_key)
        return private_key_object.public_key

    def verify(self, message:Any, signature:str, vrs:Union[tuple, list], address:str) -> bool:
        '''
        verify message from the signature or vrs based on the address
        '''
        recovered_address = Account.recover_message(message, vrs=vrs, signature=signature)
        return bool(recovered_address == address)
    
    @classmethod
    def password2private_key(cls, password, salt = 'eth'):
        from Crypto.Protocol.KDF import PBKDF2
        return  PBKDF2(password.encode(), salt, dkLen=32, count=100000).hex()
    
    @classmethod
    def from_password(cls, password:str, salt = 'eth'):
        return cls.from_key(cls.password2private_key(password, salt))

    @classmethod
    def create(cls, extra_entropy=""):
        r"""
        Creates a new private key, and returns it as a
        :class:`~eth_account.local.Key`.
        :type extra_entropy: str or bytes or int
        """
        extra_key_bytes = text_if_str(to_bytes, extra_entropy)
        key_bytes = keccak(os.urandom(32) + extra_key_bytes)
        return cls.from_key(key_bytes)


    @classmethod
    def new(cls, extra_entropy=""):
        extra_key_bytes = text_if_str(to_bytes, extra_entropy)
        key_bytes = keccak(os.urandom(32) + extra_key_bytes)
        return cls.from_key(key_bytes)

    @classmethod
    def create_private_key(cls, extra_entropy="", return_str=False):
        extra_key_bytes = text_if_str(to_bytes, extra_entropy)
        private_key = keccak(os.urandom(32) + extra_key_bytes)
        if return_str:
            return private_key.hex()
        return private_key
    
    @classmethod
    def hex2str(self, hex_str):
        return bytes.fromhex(hex_str).decode()
    
    @classmethod
    def str2hex(self, string):
        from hexbytes.main import HexBytes
        return HexBytes(string).hex()

    @combomethod
    def from_mnemonic(
        self,
        mnemonic: str,
        passphrase: str = "",
        account_path: str = ETHEREUM_DEFAULT_PATH,
    ) -> 'Key':
        """
        :param str mnemonic: space-separated list of BIP39 mnemonic seed words
        :param str passphrase: Optional passphrase used to encrypt the mnemonic
        :param str account_path: Specify an alternate HD path for deriving the seed
            using BIP32 HD wallet key derivation.
        :return: object with methods for signing and encrypting
        :rtype: Key
        """
        if not self._use_unaudited_hdwallet_features:
            raise AttributeError(
                "The use of the Mnemonic features of Account is disabled by "
                "default until its API stabilizes. To use these features, please "
                "enable them by running `Account.enable_unaudited_hdwallet_features()` "
                "and try again."
            )
        seed = seed_from_mnemonic(mnemonic, passphrase)
        private_key = key_from_seed(seed, account_path)
        key = self._parsePrivateKey(private_key)
        return Key(key)


    def __str__(self):
        return f'Key(address={self.address} name={self.name}, crypto_type={self.crypto_type})'
    

    def __repr__(self):
        return self.__str__()
    
    def resolve_encryption_password(self, password:str=None):
        password = password or self.private_key_string
        if isinstance(password, str):
            password = password.encode()
        return hashlib.sha256(password).digest()
    
    def resolve_encryption_data(self, data):
        if not isinstance(data, str):
            data = str(data)
        return data

    def encrypt(self, data, password=None):
        data = self.resolve_encryption_data(data)
        password = self.resolve_encryption_password(password)
        data = data + (AES.block_size - len(data) % AES.block_size) * chr(AES.block_size - len(data) % AES.block_size)
        iv = Random.new().read(AES.block_size)
        cipher = AES.new(password, AES.MODE_CBC, iv)
        encrypted_bytes = base64.b64encode(iv + cipher.encrypt(data.encode()))
        return encrypted_bytes.decode() 

    def decrypt(self, data, password=None):
        data = self.resolve_encryption_data(data)
        password = self.resolve_encryption_password(password)
        data = base64.b64decode(data)
        iv = data[:AES.block_size]
        cipher = AES.new(password, AES.MODE_CBC, iv)
        data =  cipher.decrypt(data[AES.block_size:])
        data = data[:-ord(data[len(data)-1:])].decode('utf-8')
        return data

    
    def save_key(self, name, private_key=None):
        if private_key:
            self.private_key = private_key
        path = c.resolve_path(f'eth/{name}')
        data = {'private_key': self.private_key}
        c.put_json(path, data)
        return self.private_key
    
    def to_dict(self):
        return {
            'address': self.address,
            'private_key': self.private_key_string
        }
    
    
    @classmethod
    def from_key(cls, private_key:str):
        key = Key(private_key)
        print(key.address)
        return key
    
    @classmethod
    def from_dict(cls, data):
        key = Key.from_key(data['private_key'])
        assert key.address == data['address'], f'{key.address} != {data["address"]}'
        self = key
        return self
    
    @classmethod
    def get_key_path(cls, name):
        path =  f'{cls.key_storage_path}/{name}.json'
        return c.resolve_path(path)
    
    def get_keys(self, password=None):
        key2encrypted = self.key2encrypted()
        key2address = {}
        for k, enc in key2encrypted.items():
            if enc :
                try:
                    key2address[k] = self.get_key(k, password)
                except :
                    pass
        return key2address

    def key_info(self, name):
        path = self.get_key_path(name)
        return  c.get_json(path)
    
    @classmethod
    def get_key(cls, name, password=None, create_if_not_found=True):
        path = cls.get_key_path(name)
        if not os.path.exists(path):
            if create_if_not_found:
                cls.add_key(name)
            else:
                raise Exception(f'Key {name} not found')
        data = c.get_json(path)
        if password != None:
            # assert data['encrypted']
            data['private_key'] = c.decrypt(data['private_key'], password=password)
            
        key =  cls.from_dict(data)
        key.name = name
        return key
    @classmethod
    def add_key(self, name, key=None, refresh=False):
        data = Key(key).to_dict()
        path = self.get_key_path(name)
        if os.path.exists(path) and not refresh:
            raise Exception(f'Key {name} already exists')
        c.put_json(path, data)
        return {'status': 'success', 'message': f'Key {name} added'}
    @classmethod
    def key_exists(self, name):
        path = self.get_key_path(name)
        return os.path.exists(path)
    
    def load_key(self, name):
        path = self.get_key_path(name)
        data = c.get_json(path)
        self.private_key = data['private_key']
        return {'status': 'success', 'message': f'Key {name} loaded', 'address': self.address}
    
    @classmethod
    def key2path(cls):
        cls.key_storage_path = c.resolve_path(cls.key_storage_path)
        paths = c.ls(cls.key_storage_path)
        key2path = {path.split('/')[-1].split('.')[0]: path for path in paths}
        return key2path

    @classmethod
    def keys(cls, search=None, show_encrypted=False):
        keys = list(cls.key2path().keys())
        key2encrypted = cls.key2encrypted()
        if not show_encrypted:
            keys = [key  for key in keys if not key2encrypted[key]]
        if search:
            keys = list(filter(lambda k: search in k, keys))
        return keys

    @classmethod
    def remove_key(cls, name):
        return os.remove(cls.get_key_path(name))
    
    @classmethod
    def is_encrypted(cls, key):
        if isinstance(key, str):
            key2path = cls.key2path()
            if key not in key2path:
                return False
            path = key2path[key]
            if not os.path.exists(path) :
                return False
            data = c.get_json(path)
        return bool(isinstance(data, dict) and data.get('encrypted', False))
    
    @classmethod
    def key2encrypted(cls ):
        key2path = cls.key2path()
        key2path = {key: cls.is_encrypted(key) for key, path in key2path.items() }
        return key2path
    
    @classmethod
    def encrypted_keys(cls):
        return [key for key, encrypted in cls.key2encrypted().items() if encrypted]

    def encrypt_key(self, name, password=None):
        assert self.key_exists(name), f'Key {name} not found'
        assert not self.is_encrypted(name), f'Key {name} is already encrypted'
        path = self.get_key_path(name)
        data = c.get_json(path)
        data['private_key'] = self.encrypt(data['private_key'], password)
        data['encrypted'] = True
        c.put_json(path, data)
        return {'status': 'success', 'message': f'Key {name} encrypted'}
    
    def decrypt_key(self, name, password=None, save=True):
        path = self.get_key_path(name)
        import json
        data = json.loads(c.get_text(path))
        if 'private_key' in data:
            data['private_key'] = self.decrypt(data['private_key'], password=password)
        else:
            data = self.decrypt(data, password=password)
        data['encrypted'] = False
        if save:
            c.put_json(path, data)
        return {'status': 'success', 'message': f'Key {name} decrypted'}
                
    def key2data(self, password=None):
        key2data = {}
        for key, path in self.key2path().items():
            data = c.get_json(path)
            if data == None:
                continue
            if password != None and data.get('encrypted', False) == True:
                try:
                    data['private_key'] = self.decrypt(data['private_key'], password=password)
                    assert Key(data['private_key']).address == data['address']
                except Exception as e:
                    data = None
                    print(e)
                    pass
            if data != None:
                key2data[key] = data
        return key2data
    