# 📦 Blockchain – Function Overview

This Python-based blockchain implementation supports transactions, mining (Proof of Work), and peer-to-peer synchronization via a simple Flask API.

---

## 🔧 Core Functions

### `__init__(self)`
Initializes the blockchain:
- `self.chain`: the list of all blocks  
- `self.current_transactions`: pending transactions  
- `self.nodes`: set of registered peer nodes  
- Automatically creates the genesis block.

---

### `new_transaction(sender, recipient, amount, order)`
Adds a new transaction to the pool of pending transactions.

**Returns:**  
The index of the block where the transaction will be recorded.

---

### `new_block(proof, previous_hash)`
Creates a new block containing current transactions.

**Includes:**  
Index, timestamp, transactions, proof, and previous hash.

---

### `proof_of_work(last_block)`
Performs brute-force search for a valid proof such that the resulting hash starts with `"0000"`.

---

### `valid_proof(last_proof, proof, last_hash)`
Checks if a proposed proof is valid by hashing it with the previous proof and block hash.

---

### `hash(block)`
Returns the SHA-256 hash of a block with consistent formatting using sorted keys.

---

### `valid_chain(chain)`
Verifies that a blockchain is valid by checking:
- Hash links between blocks  
- Valid proof-of-work for each block

---

### `resolve_conflicts()`
Consensus method that replaces the local chain if a longer valid one is found among registered nodes.

---

### `register_node(address)`
Registers a new peer node to enable future synchronization.

---

## 🌐 API Endpoints (Flask)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/mine` | GET | Mines a new block |
| `/transactions/new` | POST | Adds a new transaction |
| `/chain` | GET | Returns the full blockchain |
| `/nodes/register` | POST | Registers peer nodes |
| `/nodes/resolve` | GET | Runs the consensus algorithm |

---
