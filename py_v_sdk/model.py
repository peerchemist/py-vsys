"""
model contains data model related resources.
"""
from __future__ import annotations
import abc
import time
from typing import Any, NamedTuple

import base58

from py_v_sdk import chain as ch
from py_v_sdk.utils.crypto import hashes as hs


class Model(abc.ABC):
    """
    Model is the base class for data models that provides self-validation methods
    and other handy methods(e.g. converts bytes to base58 string).

    NOTE that the validate() method is deliberately called within the constructor so as
    to avoid accidental malformed data as much as possible.
    """

    def __init__(self, data: Any) -> None:
        """
        Args:
            data (Any): The data to contain.
        """
        self.data = data
        self.validate()

    @abc.abstractmethod
    def validate(self) -> None:
        """
        validate validates the containing data.
        """

    def __str__(self) -> str:
        """
        E.g. Str('hello')
        """
        cls_name = self.__class__.__name__
        return f"{cls_name}({self.data})"


class Str(Model):
    """
    Str is the data model for string.
    """

    def __init__(self, data: str = "") -> None:
        """
        Args:
            data (str, optional): The data to contain. Defaults to "".
        """
        self.data = data
        self.validate()

    @classmethod
    def from_bytes(cls, b: bytes) -> Str:
        """
        from_bytes parses the given bytes and creates a Str.

        Args:
            b (bytes): The bytes to parse.

        Returns:
            Str: The Str instance.
        """
        return cls(b.decode("latin-1"))

    @property
    def bytes(self) -> bytes:
        """
        bytes returns the bytes representation of the containing data.

        Returns:
            bytes: The bytes representation.
        """
        return self.data.encode("latin-1")

    @property
    def b58_str(self) -> str:
        """
        b58_str returns the base58 string representation of the containing data.

        Returns:
            str: The base58 string representation.
        """
        return base58.b58encode(self.data).decode("latin-1")

    def validate(self) -> None:
        cls_name = self.__class__.__name__

        if not isinstance(self.data, str):
            raise TypeError(f"Data in {cls_name} must be a str")


class B58Str(Str):
    """
    B58Str is the data model for base58 string.
    """

    @classmethod
    def from_bytes(cls, b: bytes) -> B58Str:
        """
        from_bytes parses the given bytes and creates a B58Str.

        Args:
            b (bytes): The bytes to parse.

        Returns:
            B58Str: The B58Str instance.
        """
        return cls(base58.b58encode(b).decode("latin-1"))

    @property
    def bytes(self) -> bytes:
        """
        bytes returns the bytes representation of the containing data.

        Returns:
            bytes: The bytes representation.
        """
        return base58.b58decode(self.data)

    def validate(self) -> None:
        super().validate()
        cls_name = self.__class__.__name__

        try:
            self.bytes
        except ValueError:
            raise ValueError(f"Data in {cls_name} must be base58-decodable")


class FixedSizeB58Str(B58Str):
    """
    FixedSizeB58Str is the data model for fixed-size base58 string.
    """

    BYTES_LEN = 0

    def validate(self) -> None:
        super().validate()
        cls_name = self.__class__.__name__

        if not len(self.bytes) == self.BYTES_LEN:
            raise ValueError(
                f"Data in {cls_name} must be exactly {self.BYTES_LEN} bytes after base58 decode"
            )


class Addr(FixedSizeB58Str):
    """
    Addr is the data model for an address.
    """

    VER = 5
    VER_BYTES_LEN = 1
    CHAIN_ID_BYTES_LEN = 1
    PUB_KEY_HASH_BYTES_LEN = 20
    CHECKSUM_BYTES_LEN = 4
    BYTES_LEN = (
        VER_BYTES_LEN + CHAIN_ID_BYTES_LEN + PUB_KEY_HASH_BYTES_LEN + CHECKSUM_BYTES_LEN
    )

    @property
    def version(self) -> int:
        """
        version returns the version of the address.

        Returns:
            int: The version.
        """
        return self.bytes[0]

    @property
    def chain_id(self) -> str:
        """
        chain_id returns the chain ID of the address.

        Returns:
            str: The chain ID.
        """
        return chr(self.bytes[1])

    @property
    def pub_key_hash(self) -> bytes:
        """
        pub_key_hash returns the hash of the public key of the address.

        Returns:
            bytes: The hash.
        """
        prev_len = self.VER_BYTES_LEN + self.CHAIN_ID_BYTES_LEN
        b = self.bytes[prev_len:]
        return b[: self.PUB_KEY_HASH_BYTES_LEN]

    @property
    def checksum(self) -> bytes:
        """
        checksum returns the checksum of the address.

        Returns:
            bytes: The checksum.
        """
        return self.bytes[-self.CHECKSUM_BYTES_LEN :]

    def must_on(self, chain: ch.Chain):
        """
        must_on asserts that the address must be on the given chain.

        Args:
            chain (ch.Chain): The chain object.

        Raises:
            ValueError: If the address is not on the given chain.
        """
        if self.chain_id != chain.chain_id.value:
            raise ValueError(
                f"Addr is not on the chain. The Addr has chain_id '{self.chain_id}' while the chain expects '{chain.chain_id.value}'"
            )

    def validate(self) -> None:
        super().validate()
        cls_name = self.__class__.__name__

        if self.version != self.VER:
            raise ValueError(f"Data in {cls_name} has invalid address version")

        chain_id_valid = any([self.chain_id == c.value for c in ch.ChainID])
        if not chain_id_valid:
            raise ValueError(f"Data in {cls_name} has invalid chain_id")

        def ke_bla_hash(b: bytes) -> bytes:
            return hs.keccak256_hash(hs.blake2b_hash(b))

        cl = self.CHECKSUM_BYTES_LEN
        if self.bytes[-cl:] != ke_bla_hash(self.bytes[:-cl])[:cl]:
            raise ValueError(f"Data in {cls_name} has invalid checksum")


class CtrtID(FixedSizeB58Str):
    """
    CtrtID is the data model for contract ID.
    """

    BYTES_LEN = 26


class TokenID(FixedSizeB58Str):
    """
    TokenID is the data model for token ID.
    """

    BYTES_LEN = 30


class PubKey(FixedSizeB58Str):
    """
    PubKey is the data model for public key.
    """

    BYTES_LEN = 32


class PriKey(FixedSizeB58Str):
    """
    PriKey is the data model for private key.
    """

    BYTES_LEN = 32


class Int(Model):
    """
    Int is the data model for an integer.
    """

    def __init__(self, data: int = 0) -> None:
        """
        Args:
            data (int, optional): The data to contain. Defaults to 0.
        """
        self.data = data
        self.validate()

    def validate(self) -> None:
        cls_name = self.__class__.__name__
        if not isinstance(self.data, int):
            raise TypeError(f"Data in {cls_name} must be an int")


class NonNegativeInt(Int):
    """
    NonNegativeInt is the data model for a non-negative integer.
    """

    def validate(self) -> None:
        super().validate()
        cls_name = self.__class__.__name__

        if not self.data >= 0:
            raise ValueError(f"Data in {cls_name} must be non negative")


class TokenIdx(NonNegativeInt):
    """
    TokenIdx is the data model for token index.
    """

    pass


class Nonce(NonNegativeInt):
    """
    Nonce is the data model for nonce (used with seed for an account).
    """

    pass


class VSYSTimestamp(NonNegativeInt):
    """
    VSYSTimestamp is the data model for the timestamp used in VSYS.
    """

    SCALE = 1_000_000_000

    @classmethod
    def from_unix_ts(cls, ux_ts: int | float) -> VSYSTimestamp:
        """
        from_unix_ts creates a new VSYSTimestamp from the given UNIX timestamp.

        Args:
            ux_ts (int | float): The UNIX timestamp.

        Raises:
            TypeError: If the type of the given UNIX timestamp is neither int nor float.
            ValueError: If the given UNIX timestamp is not positive.

        Returns:
            VSYSTimestamp: The VSYSTimestamp.
        """
        if not (isinstance(ux_ts, int) or isinstance(ux_ts, float)):
            raise TypeError("ux_ts must be an int or float")

        if ux_ts <= 0:
            raise ValueError("ux_ts must be greater than 0")

        return cls(int(ux_ts * cls.SCALE))

    @classmethod
    def now(cls) -> VSYSTimestamp:
        """
        now creates a new VSYSTimestamp for current time.

        Returns:
            VSYSTimestamp: The VSYSTimestamp.
        """
        return cls(int(time.time() * cls.SCALE))

    def validate(self) -> None:
        super().validate()
        cls_name = self.__class__.__name__

        if self.data <= self.SCALE:
            raise ValueError(f"Data in {cls_name} must be greater than {self.SCALE}")


class VSYS(NonNegativeInt):
    """
    VSYS is the data model for VSYS(the native token on VSYS blockchain).
    """

    UNIT = 1_00_000_000

    @classmethod
    def one(cls) -> VSYS:
        """
        one creates a new VSYS where the denomination is equal to ONE VSYS coin on the VSYS blockchain.

        Returns:
            VSYS: The VSYS.
        """
        return cls(cls.UNIT)

    @property
    def amount(self) -> float:
        """
        amount returns the amount of VSYS coins the VSYS object represents.

        Returns:
            float: The amount of VSYS coins.
        """
        return self.data / self.UNIT

    def __mul__(self, factor: int | float) -> VSYS:
        """
        __mul__ defiens the behaviour of the '*' operator.

        E.g.
            v1 = VSYS.one()
            v20 = v1 * 20
            v2 = v20 * 0.1

        Args:
            factor (int | float): The factor to multiply.

        Returns:
            VSYS: The result of the multiplication.
        """
        return self.__class__(int(self.data * factor))


class Fee(VSYS):
    """
    Fee is the data model for transaction fee.
    """

    DEFAULT = int(VSYS.UNIT * 0.1)

    def __init__(self, data: int = 0) -> None:
        """
        Args:
            data (int, optional): The data to contain. Defaults to 0.
        """
        if data == 0:
            data = self.DEFAULT
        super().__init__(data)

    def validate(self) -> None:
        super().validate()
        cls_name = self.__class__.__name__

        if not self.data >= self.DEFAULT:
            raise ValueError(
                f"Data in {cls_name} must be equal or greater than {self.DEFAULT}"
            )


class RegCtrtFee(Fee):
    """
    RegCtrtFee is the data model for the fee of a transaction where the type is Register Contract.
    """

    DEFAULT = VSYS.UNIT * 100


class ExecCtrtFee(Fee):
    """
    ExecCtrtFee is the data model for the fee of a transaction where the type is Execute Contract.
    """

    DEFAULT = int(VSYS.UNIT * 0.3)


class ContendSlotsFee(Fee):
    """
    ContendSlotsFee is the data model for the fee of a transaction where the type is Contend Slots.
    """

    DEFAULT = VSYS.UNIT * 50_000


class DBPutFee(Fee):
    """
    DBPutFee is the data model for the fee of a transaction where the type is DB Put.
    """

    DEFAULT = VSYS.UNIT


class Bytes(Model):
    """
    Bytes is the data model for bytes.
    """

    def __init__(self, data: bytes = b"") -> None:
        """
        Args:
            data (bytes, optional): The data to contain. Defaults to b"".
        """
        self.data = data
        self.validate()

    @property
    def b58_str(self) -> str:
        """
        b58_str returns the base58 string representation of the containing data.

        Returns:
            str: The base58 string representation.
        """
        return base58.b58encode(self.data).decode("latin-1")

    def validate(self) -> None:
        cls_name = self.__class__.__name__

        if not isinstance(self.data, bytes):
            raise TypeError(f"Data in {cls_name} must be bytes")


class Bool(Model):
    """
    Bool is the data model for a boolean value.
    """

    def __init__(self, data: bool = False) -> None:
        """
        Args:
            data (bool, optional): The data to contain. Defaults to False.
        """
        self.data = data
        self.validate()

    def validate(self) -> None:
        cls_name = self.__class__.__name__

        if not isinstance(self.data, bool):
            raise TypeError(f"Data in {cls_name} must be a bool")


class KeyPair(NamedTuple):
    """
    KeyPair is the data model for a key pair(public / private keys).
    """

    pub: PubKey
    pri: PriKey