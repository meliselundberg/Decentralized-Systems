import hashlib
import json
from time import time
from urllib.parse import urlparse
from uuid import uuid4
import random
import requests
from flask import Flask, jsonify, request, send_file


class Blockchain:
    def __init__(self):
        self.current_transactions = []
        self.chain = []
        self.nodes = set()
        self.stakes = {}
        self.seen_stakes = set()

        # Create the genesis block
        genesis_block = {
            'index': 1,
            'timestamp': 0,
            'transactions': [],
            'validator': 'genesis',
            'previous_hash': '1',
        }
        self.chain.append(genesis_block)

    def register_node(self, address):
        """
        Add a new node to the list of nodes.

        Ensures that nodes are stored as host:port, e.g. 'localhost:5001'.
        """
        parsed_url = urlparse(address)

        if parsed_url.scheme and parsed_url.netloc:
            node = parsed_url.netloc
        elif parsed_url.path:
            node = parsed_url.path
        else:
            raise ValueError("Invalid URL")

        # Ensure proper formatting
        if not node.startswith("localhost") and not node.startswith("127.0.0.1"):
            node = f"localhost:{node}"

        self.nodes.add(node)

    def resolve_conflicts(self):
    # Consensus algorithm: replaces our chain with the longest valid one,
    # or with an equally long chain that has higher total stake.
        print(f"[DEBUG] Resolving conflicts with peers: {self.nodes}")
        neighbours = self.nodes
        new_chain = None

        max_length = len(self.chain)
        current_stake = self.total_stake(self.chain)

        for node in neighbours:
            try:
                response = requests.get(f'http://{node}/chain')
                if response.status_code != 200:
                    continue

                length = response.json()['length']
                chain = response.json()['chain']

                if self.valid_chain(chain):
                    their_stake = self.total_stake(chain)

                    if length > max_length or (length == max_length and their_stake > current_stake):
                        max_length = length
                        current_stake = their_stake
                        new_chain = chain

            except requests.exceptions.RequestException as e:
                print(f"[ERROR] Exception while contacting {node}: {e}")
                continue

        if new_chain:
            self.chain = new_chain
            return True

        return False

    
    def total_stake(self, chain):
    # Sum all reward transactions (sender == '0') to estimate total validator rewards.
        return sum(
            tx['amount']
            for block in chain
            for tx in block.get('transactions', [])
            if tx.get('sender') == '0'
        )

    def new_block(self, validator, previous_hash):
        block = {
            'index': len(self.chain) + 1,
            'timestamp': time(),
            'transactions': self.current_transactions,
            'validator': validator,
            'previous_hash': previous_hash or self.hash(self.chain[-1]),
        }
        self.current_transactions = []
        self.chain.append(block)
        return block
    
    # New logic PoS
    def register_stake(self, node_id, amount):
        if node_id in self.stakes:
            self.stakes[node_id] += amount
        else:
            self.stakes[node_id] = amount


    def choose_validator(self):
        total_stake = sum(self.stakes.values())
        if total_stake == 0:
            return None
        weighted_choices = [(node, stake / total_stake) for node, stake in self.stakes.items()]
        rand = random.random()
        cumulative = 0.0
        for node, weight in weighted_choices:
            cumulative += weight
            if rand < cumulative:
                return node
        return None

    def new_transaction(self, sender, recipient, amount, order):
        """
        Creates a new transaction to go into the next mined Block

        :param sender: Address of the Sender
        :param recipient: Address of the Recipient
        :param amount: Amount
        :param order: Order number
        :return: The index of the Block that will hold this transaction
        """
        
        transaction = {
            'sender': sender,
            'recipient': recipient,
            'amount': amount,
            'order': order,    
        }
        
        self.current_transactions.append(transaction)

        return self.last_block['index'] + 1

    def valid_chain(self, chain):
        last_block = chain[0]
        current_index = 1

        while current_index < len(chain):
            block = chain[current_index]

            # Check that the previous_hash is correct
            if block['previous_hash'] != self.hash(last_block):
                return False

            last_block = block
            current_index += 1

        return True

    @property
    def last_block(self):
        return self.chain[-1]

    @staticmethod
    def hash(block):
        """
        Creates a SHA-256 hash of a Block

        :param block: Block
        """
        # We must make sure that the Dictionary is Ordered, or we'll have inconsistent hashes
        block_string = json.dumps(block, sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()

    # def proof_of_work(self, last_block):
    #     """
    #     Simple Proof of Work Algorithm:

    #      - Find a number p' such that hash(pp') contains leading 4 zeroes
    #      - Where p is the previous proof, and p' is the new proof

    #     :param last_block: <dict> last Block
    #     :return: <int>
    #     """

    #     last_proof = last_block['proof']
    #     last_hash = self.hash(last_block)

    #     proof = 0
    #     while self.valid_proof(last_proof, proof, last_hash) is False:
    #         proof += 1

    #     return proof

    # @staticmethod
    # def valid_proof(last_proof, proof, last_hash):
    #     """
    #     Validates the Proof

    #     :param last_proof: <int> Previous Proof
    #     :param proof: <int> Current Proof
    #     :param last_hash: <str> The hash of the Previous Block
    #     :return: <bool> True if correct, False if not.

    #     """

    #     guess = f'{last_proof}{proof}{last_hash}'.encode()
    #     guess_hash = hashlib.sha256(guess).hexdigest()
    #     return guess_hash[:4] == "0000"


# Instantiate the Node
port = None  # Will be assigned in __main__
app = Flask(__name__)

# Generate a globally unique address for this node
node_identifier = str(uuid4()).replace('-', '')

# Instantiate the Blockchain
blockchain = Blockchain()

@app.route('/validate', methods=['POST'])
def validate():
    validator = blockchain.choose_validator()
    if not validator:
        return jsonify({'message': 'No validators available'}), 400

    blockchain.new_transaction(
        sender="0",
        recipient=validator,
        amount=1,
        order=0,
    )
    previous_hash = blockchain.hash(blockchain.last_block)
    block = blockchain.new_block(validator, previous_hash)

    # Sync chain with all peers
    for node in blockchain.nodes:
        try:
            requests.get(f'http://{node}/nodes/resolve')
        except requests.exceptions.RequestException as e:
            print(f"[ERROR] Failed to sync with {node}: {e}")
            pass

    response = {
        'message': f'Block validated by {validator}',
        'index': block['index'],
        'transactions': block['transactions'],
        'validator': block['validator'],
        'previous_hash': block['previous_hash'],
    }
    return jsonify(response), 200

@app.route('/transactions/new', methods=['POST'])
def new_transaction():
    values = request.get_json()
    required = ['sender', 'recipient', 'amount', 'order']
    if not all(k in values for k in required):
        return 'Missing values', 400

    # Avoid rebroadcasting if already propagated
    propagated = values.get('propagated', False)
    
    index = blockchain.new_transaction(
        values['sender'],
        values['recipient'],
        values['amount'],
        values['order']
    )

    if not propagated:
        for node in blockchain.nodes:
            try:
                forwarded = values.copy()
                forwarded['propagated'] = True
                requests.post(f'http://{node}/transactions/new', json=forwarded)
            except requests.exceptions.RequestException:
                print(f"[ERROR] Failed to broadcast to {node}")

    return jsonify({'message': f'Transaction will be added to Block {index}'}), 201

@app.route('/chain', methods=['GET'])
def full_chain():
    response = {
        'chain': blockchain.chain,
        'length': len(blockchain.chain),
    }
    return jsonify(response), 200


@app.route('/nodes/register', methods=['POST'])
def register_nodes():
    values = request.get_json()

    nodes = values.get('nodes')
    if nodes is None:
        return "Error: Please supply a valid list of nodes", 400
    blockchain.register_node(nodes)

    response = {
        'message': 'New nodes have been added',
        'total_nodes': list(blockchain.nodes),
    }
    return jsonify(response), 201


@app.route('/nodes/resolve', methods=['GET'])
def consensus():
    replaced = blockchain.resolve_conflicts()

    if replaced:
        response = {
            'message': 'Our chain was replaced',
            'new_chain': blockchain.chain
        }
    else:
        response = {
            'message': 'Our chain is authoritative',
            'chain': blockchain.chain
        }
    return jsonify(response), 200

@app.route('/stake', methods=['POST'])
def stake_tokens():
    values = request.get_json()
    required = ['node_id', 'amount']
    if not all(k in values for k in required):
        return 'Missing values', 400

    # Avoid infinite rebroadcast
    propagated = values.get('propagated', False)

    blockchain.register_stake(values['node_id'], values['amount'])

    # Only broadcast if this is the original request
    if not propagated:
        for node in blockchain.nodes:
            try:
                forwarded = values.copy()
                forwarded['propagated'] = True
                requests.post(f'http://{node}/stake', json=forwarded)
            except requests.exceptions.RequestException as e:
                print(f"[ERROR] Failed to broadcast stake to {node}: {e}")

    return jsonify({'message': f"{values['node_id']} staked {values['amount']}"}), 201

@app.route('/gui', methods=['GET'])
def gui():
    return send_file('index.html')
#Display the node id in the GUI for verification of PoS
@app.route('/id', methods=['GET'])
def get_node_id():
    return jsonify({'node_id': node_identifier})

#Allows you to remove your staked tokens
@app.route('/unstake', methods=['POST'])
def unstake_tokens():
    values = request.get_json()
    node_id = values.get('node_id')

    if not node_id:
        return 'Missing node_id', 400

    current_stake = blockchain.stakes.get(node_id, 0)
    if current_stake == 0:
        return jsonify({'message': 'No tokens to unstake'}), 400

    blockchain.stakes[node_id] = 0

    return jsonify({'message': f'All tokens unstaked from {node_id}'}), 200

#Displays the current stake status of all nodes
@app.route('/stake/status', methods=['GET'])
def stake_status():
    return jsonify(blockchain.stakes), 200

if __name__ == '__main__':
    from argparse import ArgumentParser

    parser = ArgumentParser()
    parser.add_argument('-p', '--port', default=5000, type=int, help='port to listen on')
    args = parser.parse_args()

    # Set global port
    globals()['port'] = args.port

    app.run(host='0.0.0.0', port=port)
