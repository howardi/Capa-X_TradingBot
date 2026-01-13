import '@rainbow-me/rainbowkit/styles.css';
import { getDefaultConfig } from '@rainbow-me/rainbowkit';
import {
  mainnet,
  polygon,
  optimism,
  arbitrum,
  base,
} from 'wagmi/chains';

export const config = getDefaultConfig({
  appName: 'CapaRox Trading Bot',
  projectId: '3fcc6bba6f1de962d911bb5b5c3dba68', // Example public Project ID for demo
  chains: [mainnet, polygon, optimism, arbitrum, base],
});
