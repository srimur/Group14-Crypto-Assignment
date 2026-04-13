import time
import json
from crypto_utils.sha3_utils import sha3_hash, transaction_hash


class Block:

    def __init__(self, index: int, transaction_data: dict,
                 previous_hash: str, timestamp: float = None):
        self.index = index
        self.timestamp = timestamp or time.time()
        self.transaction_data = transaction_data
        self.previous_hash = previous_hash

        self.transaction_id = transaction_hash(
            transaction_data.get("uid", ""),
            transaction_data.get("fid", ""),
            self.timestamp,
            transaction_data.get("amount", 0),
        )

        self.dispute_flag = transaction_data.get("dispute", False)
        self.hash = self.compute_hash()

    def compute_hash(self) -> str:
        block_string = json.dumps({
            "index": self.index,
            "timestamp": self.timestamp,
            "transaction_id": self.transaction_id,
            "transaction_data": self.transaction_data,
            "previous_hash": self.previous_hash,
            "dispute_flag": self.dispute_flag,
        }, sort_keys=True)
        return sha3_hash(block_string)

    def __repr__(self):
        dispute_str = " [DISPUTE/REFUND]" if self.dispute_flag else ""
        return (
            f"Block #{self.index}{dispute_str}\n"
            f"  Txn ID     : {self.transaction_id[:32]}...\n"
            f"  Timestamp  : {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(self.timestamp))}\n"
            f"  Data       : UID={self.transaction_data.get('uid', 'N/A')}, "
            f"FID={self.transaction_data.get('fid', 'N/A')}, "
            f"Amount=₹{self.transaction_data.get('amount', 0):.2f}\n"
            f"  Prev Hash  : {self.previous_hash[:32]}...\n"
            f"  Block Hash : {self.hash[:32]}..."
        )


class Blockchain:

    def __init__(self):
        self.chain = []
        self._create_genesis_block()

    def _create_genesis_block(self):
        genesis_data = {
            "uid": "0" * 16,
            "fid": "0" * 16,
            "amount": 0.0,
            "description": "Genesis Block - Grid Authority Initialized",
            "dispute": False,
        }
        genesis_block = Block(0, genesis_data, "0" * 64)
        self.chain.append(genesis_block)

    @property
    def last_block(self) -> Block:
        return self.chain[-1]

    def add_transaction(self, uid: str, fid: str, amount: float,
                        description: str = "", dispute: bool = False) -> Block:
        transaction_data = {
            "uid": uid,
            "fid": fid,
            "amount": amount,
            "description": description,
            "dispute": dispute,
        }
        new_block = Block(
            index=len(self.chain),
            transaction_data=transaction_data,
            previous_hash=self.last_block.hash,
        )
        self.chain.append(new_block)
        return new_block

    def validate_chain(self) -> tuple:
        for i in range(1, len(self.chain)):
            current = self.chain[i]
            previous = self.chain[i - 1]

            if current.hash != current.compute_hash():
                return (False,
                        f"Block #{i} hash mismatch. Data may have been tampered.")

            if current.previous_hash != previous.hash:
                return (False,
                        f"Block #{i} previous_hash doesn't match Block #{i-1} hash.")

        return (True, "Blockchain integrity verified. All blocks are valid.")

    def get_transactions_for_user(self, uid: str) -> list:
        return [b for b in self.chain[1:] if b.transaction_data.get("uid") == uid]

    def get_transactions_for_franchise(self, fid: str) -> list:
        return [b for b in self.chain[1:] if b.transaction_data.get("fid") == fid]

    def display_chain(self):
        print(f"\n{'='*60}")
        print(f"  BLOCKCHAIN LEDGER — {len(self.chain)} blocks")
        print(f"{'='*60}")
        for block in self.chain:
            print(f"\n{block}")
        print(f"\n{'='*60}")
