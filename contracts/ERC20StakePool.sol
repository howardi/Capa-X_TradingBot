// SPDX-License-Identifier: MIT 
 pragma solidity ^0.8.20; 
 
 /** 
  * Minimal ERC20 interface 
  */ 
 interface IERC20 { 
     function totalSupply() external view returns (uint256); 
     function balanceOf(address a) external view returns (uint256); 
     function transfer(address to, uint256 amt) external returns (bool); 
     function allowance(address owner, address spender) external view returns (uint256); 
     function approve(address spender, uint256 amt) external returns (bool); 
     function transferFrom(address from, address to, uint256 amt) external returns (bool); 
     function decimals() external view returns (uint8); 
 } 
 
 /** 
  * Simple staking pool: 
  * - Users stake a stakeToken (ERC20) 
  * - Rewards accrue in rewardToken using a fixed reward rate per second 
  * - Users can stake, withdraw, claim 
  * - Owner can fund and adjust reward rate 
  * 
  * Notes: 
  * - This is a scaffold for testing/extension; perform audits for production. 
  */ 
 contract ERC20StakePool { 
     IERC20 public stakeToken; 
     IERC20 public rewardToken; 
     address public owner; 
 
     // Reward distribution 
     uint256 public rewardRatePerSecond;     // reward token units per second 
     uint256 public lastUpdateTime; 
     uint256 public rewardPerTokenStored; 
 
     // User accounting 
     mapping(address => uint256) public userStake; 
     mapping(address => uint256) public userRewardPerTokenPaid; 
     mapping(address => uint256) public rewardsAccrued; 
 
     uint256 public totalStaked; 
 
     event Staked(address indexed user, uint256 amount); 
     event Withdrawn(address indexed user, uint256 amount); 
     event RewardClaimed(address indexed user, uint256 amount); 
     event RewardRateUpdated(uint256 newRate); 
     event Funded(uint256 amount); 
 
     modifier onlyOwner() { 
         require(msg.sender == owner, "not owner"); 
         _; 
     } 
 
     modifier updateReward(address account) { 
         rewardPerTokenStored = rewardPerToken(); 
         lastUpdateTime = block.timestamp; 
         if (account != address(0)) { 
             rewardsAccrued[account] = earned(account); 
             userRewardPerTokenPaid[account] = rewardPerTokenStored; 
         } 
         _; 
     } 
 
     constructor(IERC20 _stakeToken, IERC20 _rewardToken, uint256 _rewardRatePerSecond) { 
         stakeToken = _stakeToken; 
         rewardToken = _rewardToken; 
         owner = msg.sender; 
         rewardRatePerSecond = _rewardRatePerSecond; 
         lastUpdateTime = block.timestamp; 
     } 
 
     function rewardPerToken() public view returns (uint256) { 
         if (totalStaked == 0) { 
             return rewardPerTokenStored; 
         } 
         uint256 timeDelta = block.timestamp - lastUpdateTime; 
         // scaled by 1e18 
         return rewardPerTokenStored + (timeDelta * rewardRatePerSecond * 1e18) / totalStaked; 
     } 
 
     function earned(address account) public view returns (uint256) { 
         uint256 stakeAmt = userStake[account]; 
         uint256 rptDelta = rewardPerToken() - userRewardPerTokenPaid[account]; 
         return rewardsAccrued[account] + (stakeAmt * rptDelta) / 1e18; 
     } 
 
     function stake(uint256 amount) external updateReward(msg.sender) { 
         require(amount > 0, "amount=0"); 
         totalStaked += amount; 
         userStake[msg.sender] += amount; 
         require(stakeToken.transferFrom(msg.sender, address(this), amount), "stake transfer failed"); 
         emit Staked(msg.sender, amount); 
     } 
 
     function withdraw(uint256 amount) external updateReward(msg.sender) { 
         require(amount > 0, "amount=0"); 
         require(userStake[msg.sender] >= amount, "insufficient stake"); 
         totalStaked -= amount; 
         userStake[msg.sender] -= amount; 
         require(stakeToken.transfer(msg.sender, amount), "withdraw transfer failed"); 
         emit Withdrawn(msg.sender, amount); 
     } 
 
     function claim() external updateReward(msg.sender) { 
         uint256 reward = rewardsAccrued[msg.sender]; 
         require(reward > 0, "no rewards"); 
         rewardsAccrued[msg.sender] = 0; 
         require(rewardToken.transfer(msg.sender, reward), "reward transfer failed"); 
         emit RewardClaimed(msg.sender, reward); 
     } 
 
     // Owner actions 
     function setRewardRate(uint256 newRate) external onlyOwner updateReward(address(0)) { 
         rewardRatePerSecond = newRate; 
         emit RewardRateUpdated(newRate); 
     } 
 
     function fund(uint256 amount) external onlyOwner { 
         require(rewardToken.transferFrom(msg.sender, address(this), amount), "fund transfer failed"); 
         emit Funded(amount); 
     } 
 }