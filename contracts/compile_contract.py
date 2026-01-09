import json
import os
from solcx import compile_standard, install_solc

def compile_contract():
    # 1. Configuration
    solc_version = '0.8.20'
    contract_path = 'contracts/ERC20StakePool.sol'
    contract_name = 'ERC20StakePool'
    
    print(f"Installing solc version {solc_version}...")
    install_solc(solc_version)
    
    print(f"Reading contract from {contract_path}...")
    with open(contract_path, 'r') as file:
        contract_source = file.read()

    # 2. Compile
    print("Compiling...")
    compiled_sol = compile_standard(
        {
            "language": "Solidity",
            "sources": {
                "ERC20StakePool.sol": {
                    "content": contract_source
                }
            },
            "settings": {
                "outputSelection": {
                    "*": {
                        "*": ["abi", "metadata", "evm.bytecode", "evm.sourceMap"]
                    }
                }
            },
        },
        solc_version=solc_version,
    )

    # 3. Extract and Save
    # The key in 'contracts' matches the file name provided in 'sources'
    bytecode = compiled_sol['contracts']['ERC20StakePool.sol'][contract_name]['evm']['bytecode']['object']
    abi = compiled_sol['contracts']['ERC20StakePool.sol'][contract_name]['abi']

    print("Saving artifacts...")
    
    # Save ABI
    with open(f'contracts/{contract_name}_abi.json', 'w') as f:
        json.dump(abi, f, indent=4)
        
    # Save Bytecode
    with open(f'contracts/{contract_name}_bytecode.json', 'w') as f:
        json.dump(bytecode, f)
        
    print(f"✅ Compilation Successful!")
    print(f"   ABI: contracts/{contract_name}_abi.json")
    print(f"   Bytecode: contracts/{contract_name}_bytecode.json")

if __name__ == "__main__":
    compile_contract()
