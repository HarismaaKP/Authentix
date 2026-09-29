// Deploys AuthChain to whatever network Hardhat is pointed at
// (defaults to a local Hardhat/Ganache node) and prints the ABI +
// address needed by the Flask backend's blockchain_client.py.

const fs = require("fs");
const path = require("path");
const hre = require("hardhat");

async function main() {
  const AuthChain = await hre.ethers.getContractFactory("AuthChain");
  const contract = await AuthChain.deploy();
  await contract.waitForDeployment();

  const address = await contract.getAddress();
  console.log("AuthChain deployed to:", address);

  const artifact = await hre.artifacts.readArtifact("AuthChain");
  const outPath = path.join(__dirname, "..", "..", "AuthChainABI.json");
  fs.writeFileSync(outPath, JSON.stringify(artifact.abi, null, 2));

  console.log("ABI written to", outPath);
  console.log("\nSet these before starting the Flask app to use the live chain:");
  console.log(`  RPC_URL=http://127.0.0.1:8545`);
  console.log(`  CONTRACT_ADDRESS=${address}`);
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
