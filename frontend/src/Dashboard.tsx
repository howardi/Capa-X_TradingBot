import { useEffect, useRef, useState, Component, ErrorInfo, ReactNode } from "react"; 
import { createChart, IChartApi, ColorType, ISeriesApi, CrosshairMode } from "lightweight-charts"; 
import { useNavigate } from "react-router-dom";
import { ArrowDown, Settings, Wallet, BarChart2, Activity, Zap, History, LogOut, Layers, Sun, Moon } from "lucide-react";
import { ConnectButton } from '@rainbow-me/rainbowkit';
import { useToast } from './context/ToastContext';
import { Profile } from './Profile';

// --- Types ---

interface Candle {
  time: number;
  open: number;
  high: number;
  low: number;
  close: number;
}

interface Order {
  price: number;
  amount: number;
}

interface OrderBookData {
  bids: Order[];
  asks: Order[];
}



interface MyOrder {
    id: string;
    symbol: string;
    side: string;
    price: number;
    amount: number;
    filled: number;
    status: string;
    timestamp: number;
}

interface Balances {
    USDT: number;
    NGN: number;
    BTC: number;
    ETH: number;
}



// --- Helpers ---

const getUser = () => {
    const userStr = localStorage.getItem('user');
    if (!userStr) return 'admin';
    try {
        const userObj = JSON.parse(userStr);
        return userObj.username || 'admin';
    } catch (e) {
        return userStr || 'admin';
    }
};

const getUserEmail = () => {
    const userStr = localStorage.getItem('user');
    if (!userStr) return 'user@caparox.com';
    try {
        const userObj = JSON.parse(userStr);
        return userObj.email || 'user@caparox.com';
    } catch (e) {
        return 'user@caparox.com';
    }
};

const formatMoney = (amount: number | string, currency = 'USD') => {
    const num = Number(amount);
    return new Intl.NumberFormat('en-US', { style: 'currency', currency }).format(isNaN(num) ? 0 : num);
};

const normalizeBalances = (data: any): Balances => {
    if (!data) return { USDT: 0, NGN: 0, BTC: 0, ETH: 0 };
    
    const getVal = (key: string) => {
        // Handle CCXT structure { total: { USDT: 100 } }
        if (data.total && (typeof data.total[key] === 'number' || typeof data.total[key] === 'string')) return Number(data.total[key]);
        
        // Handle direct { USDT: 100 }
        if (typeof data[key] === 'number') return data[key];
        if (typeof data[key] === 'string') return Number(data[key]);
        
        // Handle nested { USDT: { total: 100 } }
        if (data[key] && typeof data[key] === 'object') {
             if (data[key].total !== undefined) return Number(data[key].total);
             if (data[key].free !== undefined) return Number(data[key].free);
        }
        
        return 0;
    };

    return {
        USDT: getVal('USDT'),
        NGN: getVal('NGN'),
        BTC: getVal('BTC'),
        ETH: getVal('ETH'),
    };
};

// --- Components ---

class ErrorBoundary extends Component<{ children: ReactNode }, { hasError: boolean, error: Error | null }> {
  constructor(props: { children: ReactNode }) {
    super(props);
    this.state = { hasError: false, error: null };
  }
  static getDerivedStateFromError(error: Error) { return { hasError: true, error }; }
  componentDidCatch(error: Error, errorInfo: ErrorInfo) { console.error("Uncaught error:", error, errorInfo); }
  render() {
    if (this.state.hasError) {
      return (
        <div className="flex flex-col items-center justify-center h-screen bg-gray-900 text-white p-8">
          <h1 className="text-3xl font-bold text-red-500 mb-4">Something went wrong.</h1>
          <pre className="bg-gray-800 p-4 rounded text-xs text-gray-300 mb-6 overflow-auto max-w-2xl">{this.state.error?.toString()}</pre>
          <button onClick={() => window.location.reload()} className="bg-indigo-600 px-6 py-2 rounded hover:bg-indigo-700 font-bold">Reload Dashboard</button>
        </div>
      );
    }
    return this.props.children;
  }
}

const ChartPanel = ({ candles, theme = 'dark', chartType = 'candle' }: { candles: Candle[], theme?: 'light' | 'dark', chartType?: 'candle' | 'area' }) => { 
  const ref = useRef<HTMLDivElement>(null); 
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null);
  const areaSeriesRef = useRef<ISeriesApi<"Area"> | null>(null);

  const isDark = theme === 'dark';
  const bgColor = isDark ? '#0b0f19' : '#ffffff'; // Darker background
  const textColor = isDark ? '#9ca3af' : '#333333';
  const gridColor = isDark ? '#1f2937' : '#f0f0f0';

  useEffect(() => {
    if (!ref.current) return;

    const chart = createChart(ref.current, { 
      width: ref.current.clientWidth, 
      height: 500, 
      layout: { background: { type: ColorType.Solid, color: bgColor }, textColor: textColor }, 
      grid: { vertLines: { color: 'rgba(31, 41, 55, 0.4)' }, horzLines: { color: 'rgba(31, 41, 55, 0.4)' } },
      crosshair: { mode: CrosshairMode.Normal },
      timeScale: { timeVisible: true, secondsVisible: false, borderColor: gridColor },
      rightPriceScale: { borderColor: gridColor },
    }); 
    
    // Series
    let series: any;
    let areaSeries: any;

    if (chartType === 'candle') {
        series = chart.addCandlestickSeries({
            upColor: '#10b981', downColor: '#ef4444', borderVisible: false, wickUpColor: '#10b981', wickDownColor: '#ef4444',
        });
        seriesRef.current = series;
        areaSeriesRef.current = null;
    } else {
        areaSeries = chart.addAreaSeries({
            lineColor: '#6366f1', 
            topColor: 'rgba(99, 102, 241, 0.4)', 
            bottomColor: 'rgba(99, 102, 241, 0.0)',
            lineWidth: 2,
        });
        areaSeriesRef.current = areaSeries;
        seriesRef.current = null;
    }

    chartRef.current = chart;

    const handleResize = () => {
        if (ref.current) {
            chart.applyOptions({ width: ref.current.clientWidth });
        }
    };

    window.addEventListener('resize', handleResize);
    return () => {
        window.removeEventListener('resize', handleResize);
        chart.remove();
        chartRef.current = null;
        seriesRef.current = null;
        areaSeriesRef.current = null;
    }
  }, [theme, chartType]); // Re-create on theme/type change

  useEffect(() => {
    if (candles.length > 0) {
        try {
            const sortedCandles = [...candles].sort((a, b) => a.time - b.time);
            const uniqueCandles = sortedCandles.filter((v, i, a) => i === 0 || v.time !== a[i - 1].time);
            
            if (chartType === 'candle' && seriesRef.current) {
                seriesRef.current.setData(uniqueCandles as any);
            } else if (chartType === 'area' && areaSeriesRef.current) {
                const areaData = uniqueCandles.map(c => ({ time: c.time, value: c.close }));
                areaSeriesRef.current.setData(areaData as any);
            }
        } catch (e) {
            console.error("Chart data error:", e);
        }
    }
  }, [candles, chartType]);

  return <div ref={ref} className="w-full h-full" />; 
}; 

const OrderBook = ({ data }: { data: OrderBookData | null }) => ( 
  <div className="flex flex-col h-full text-xs">
    <div className="flex justify-between text-gray-500 mb-2 px-2"> 
      <span>Price (USDT)</span> 
      <span>Amount (BTC)</span> 
    </div> 
    <div className="flex-1 overflow-y-auto custom-scrollbar">
    {data && data.asks && data.bids ? (
        <div className="space-y-0.5">
            {data.asks.slice(0, 15).reverse().map((ask, i) => (
                <div key={`ask-${i}`} className="flex justify-between px-2 hover:bg-gray-800 cursor-pointer relative">
                    <span className="text-red-500 font-mono z-10">{ask.price !== undefined ? Number(ask.price).toFixed(2) : '0.00'}</span>
                    <span className="text-gray-400 font-mono z-10">{ask.amount !== undefined ? Number(ask.amount).toFixed(4) : '0.0000'}</span>
                    <div className="absolute top-0 right-0 h-full bg-red-900/20" style={{ width: `${Math.min((ask.amount || 0) * 100, 100)}%` }}></div>
                </div>
            ))}
            <div className="h-px bg-gray-700 my-2 mx-2"></div>
            {data.bids.slice(0, 15).map((bid, i) => (
                <div key={`bid-${i}`} className="flex justify-between px-2 hover:bg-gray-800 cursor-pointer relative">
                    <span className="text-green-500 font-mono z-10">{bid.price !== undefined ? Number(bid.price).toFixed(2) : '0.00'}</span>
                    <span className="text-gray-400 font-mono z-10">{bid.amount !== undefined ? Number(bid.amount).toFixed(4) : '0.0000'}</span>
                    <div className="absolute top-0 right-0 h-full bg-green-900/20" style={{ width: `${Math.min((bid.amount || 0) * 100, 100)}%` }}></div>
                </div>
            ))}
        </div>
    ) : (
        <div className="flex items-center justify-center h-full text-gray-600">Loading Book...</div>
    )}
    </div>
  </div> 
); 

const SignalCard = ({ symbol }: { symbol: string }) => {
    const [data, setData] = useState<any>(null);
    const [loading, setLoading] = useState(true);

    const playSound = (type: string) => {
        if (!window.speechSynthesis) return;
        const msg = new SpeechSynthesisUtterance();
        if (type === 'buy_alert') {
            msg.text = "Buy Signal Detected";
            msg.rate = 1.1;
        } else if (type === 'sell_alert') {
            msg.text = "Sell Signal Detected";
            msg.rate = 1.1;
        } else {
            msg.text = "New Market Alert";
        }
        window.speechSynthesis.speak(msg);
        console.log(`🔊 Playing Sound: ${type}`);
    };

    const fetchSignal = async () => {
        setLoading(true);
        try {
            const res = await fetch(`/api/analyze?symbol=${symbol}`);
            const json = await res.json();
            
            // Trigger sound if signal changed or specific sound requested
            if (json.sound && (!data || data.signal !== json.signal)) {
                playSound(json.sound);
            }
            
            setData(json);
        } catch (e) { console.error(e); }
        setLoading(false);
    };

    useEffect(() => {
        fetchSignal();
        const interval = setInterval(fetchSignal, 60000); 
        return () => clearInterval(interval);
    }, [symbol]);

    if (loading) return <div className="animate-pulse bg-gray-800 h-32 rounded-lg"></div>;
    if (!data) return null;

    return (
        <div className="bg-gray-800 rounded-lg p-4 border border-gray-700 shadow-lg">
            <div className="flex justify-between items-center mb-3">
                <div className="flex items-center gap-2">
                    <Activity size={18} className="text-indigo-400" />
                    <span className="font-bold text-gray-200">AI Signal</span>
                </div>
                <div className="flex gap-2">
                    {data.indicators?.quantum_prob > 0.8 && (
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-purple-900 text-purple-400 border border-purple-700 animate-pulse">
                            QUANTUM
                        </span>
                    )}
                    <span className={`px-2 py-0.5 rounded text-xs font-bold uppercase ${
                        data.signal === 'buy' ? 'bg-green-900 text-green-400' : 
                        data.signal === 'sell' ? 'bg-red-900 text-red-400' : 'bg-gray-700 text-gray-400'
                    }`}>
                        {data.signal}
                    </span>
                </div>
            </div>
            
            <div className="flex justify-between items-end mb-2">
                <div>
                    <div className="text-xs text-gray-500 mb-1">Sentiment</div>
                    <div className={`text-sm font-bold capitalize ${
                        data.indicators?.sentiment === 'positive' ? 'text-green-400' : 
                        data.indicators?.sentiment === 'negative' ? 'text-red-400' : 'text-gray-400'
                    }`}>
                        {data.indicators?.sentiment || 'Neutral'}
                    </div>
                </div>
                <div className="text-right">
                    <div className="text-xs text-gray-500 mb-1">Indicators</div>
                    <div className="flex gap-2 text-xs font-mono text-gray-300">
                        <span>RSI: {data.indicators?.rsi !== undefined ? Number(data.indicators.rsi).toFixed(1) : 'N/A'}</span>
                        <span>SMA: {data.indicators?.sma_10 !== undefined ? Number(data.indicators.sma_10).toFixed(0) : 'N/A'}</span>
                    </div>
                </div>
            </div>
            <p className="text-xs text-gray-400 italic mt-2 border-t border-gray-700 pt-2">{data.reason}</p>
        </div>
    );
};

const CoinbasePanel = () => {
  const [coinbaseStatus, setCoinbaseStatus] = useState<'stopped' | 'running'>('stopped');
  const [coinbaseData, setCoinbaseData] = useState<any>(null);
  const { showToast } = useToast();

  const toggleCoinbase = async () => {
    if (coinbaseStatus === 'stopped') {
        try {
            const res = await fetch('/api/coinbase/start', { method: 'POST' });
            const data = await res.json();
            if(data.status === 'success') {
                setCoinbaseStatus('running');
                showToast('Coinbase Stream Started', 'success');
            }
            else showToast("Failed to start: " + data.message, 'error');
        } catch(e) { showToast("Error starting Coinbase stream", 'error'); }
    } else {
        try {
             await fetch('/api/coinbase/stop', { method: 'POST' });
             setCoinbaseStatus('stopped');
             showToast('Coinbase Stream Stopped', 'info');
        } catch(e) { showToast("Error stopping Coinbase stream", 'error'); }
    }
  };

  useEffect(() => {
    let interval: any;
    if (coinbaseStatus === 'running') {
        interval = setInterval(async () => {
            try {
                const res = await fetch('/api/coinbase/data');
                const data = await res.json();
                setCoinbaseData(data);
            } catch(e) { console.error(e); }
        }, 1000);
    }
    return () => clearInterval(interval);
  }, [coinbaseStatus]);

  return (
    <div className="bg-gray-800 p-4 rounded border border-gray-700 mt-4">
        <div className="flex justify-between items-center mb-4">
            <h3 className="font-bold text-white flex items-center gap-2">
                <Zap size={18} className="text-blue-400" />
                Coinbase Advanced Stream
            </h3>
            <button 
                onClick={toggleCoinbase}
                className={`px-4 py-1.5 rounded text-sm font-bold transition-colors ${coinbaseStatus === 'running' ? 'bg-red-600 hover:bg-red-700' : 'bg-green-600 hover:bg-green-700'}`}
            >
                {coinbaseStatus === 'running' ? 'Stop Stream' : 'Start Stream'}
            </button>
        </div>
        
        {coinbaseStatus === 'running' && (
             <div className="bg-black p-3 rounded h-32 overflow-auto font-mono text-[10px] text-green-400 border border-gray-800">
                {coinbaseData ? (
                    <pre>{JSON.stringify(coinbaseData, null, 2)}</pre>
                ) : (
                    <div className="text-gray-500 italic">Waiting for data...</div>
                )}
            </div>
        )}
    </div>
  );
};

const WithdrawalForm = ({ username }: { username: string }) => {
    const [amount, setAmount] = useState('');
    const [bankCode, setBankCode] = useState('');
    const [accountNumber, setAccountNumber] = useState('');
    const [loading, setLoading] = useState(false);
    const { showToast } = useToast();

    const handleWithdraw = async () => {
        if (!amount || !bankCode || !accountNumber) return showToast("Fill all fields", 'warning');
        setLoading(true);
        try {
            const res = await fetch('/api/withdraw', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ 
                    username, 
                    amount, 
                    account_bank: bankCode, 
                    account_number: accountNumber,
                    provider: 'flutterwave',
                    currency: 'NGN'
                })
            });
            const data = await res.json();
            if (data.status === 'success') showToast("Withdrawal Initiated!", 'success');
            else showToast("Failed: " + data.error, 'error');
        } catch (e) { showToast("Error processing withdrawal", 'error'); }
        setLoading(false);
    };

    return (
        <div className="bg-gray-800 p-4 rounded border border-gray-700 mt-4">
            <h3 className="font-bold text-white mb-2">Withdraw NGN</h3>
            <div className="space-y-2">
                <input type="number" placeholder="Amount" className="w-full bg-gray-900 p-2 rounded text-white" value={amount} onChange={e => setAmount(e.target.value)} />
                <input type="text" placeholder="Bank Code (e.g. 044)" className="w-full bg-gray-900 p-2 rounded text-white" value={bankCode} onChange={e => setBankCode(e.target.value)} />
                <input type="text" placeholder="Account Number" className="w-full bg-gray-900 p-2 rounded text-white" value={accountNumber} onChange={e => setAccountNumber(e.target.value)} />
                <button onClick={handleWithdraw} disabled={loading} className="w-full bg-red-600 hover:bg-red-700 text-white p-2 rounded font-bold">
                    {loading ? 'Processing...' : 'Withdraw Funds'}
                </button>
            </div>
        </div>
    );
};

const ImportWalletForm = ({ username, onImport }: { username: string, onImport: () => void }) => {
    const [walletType, setWalletType] = useState('eth');
    const [privateKey, setPrivateKey] = useState('');
    const [apiKey, setApiKey] = useState('');
    const [apiSecret, setApiSecret] = useState('');
    const [name, setName] = useState('My Wallet');
    const [loading, setLoading] = useState(false);
    const { showToast } = useToast();

    const handleImport = async () => {
        setLoading(true);
        try {
            const payload: any = { username, name, type: walletType };
            if (walletType === 'eth') {
                if (!privateKey) { showToast('Private Key required', 'warning'); setLoading(false); return; }
                payload.private_key = privateKey;
            } else {
                if (!apiKey || !apiSecret) { showToast('API Key and Secret required', 'warning'); setLoading(false); return; }
                payload.api_key = apiKey;
                payload.api_secret = apiSecret;
            }

            const res = await fetch('/api/wallet/import', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const data = await res.json();
            if (data.status === 'success') {
                showToast('Wallet Imported!', 'success');
                setPrivateKey('');
                setApiKey('');
                setApiSecret('');
                onImport();
            } else {
                showToast('Error: ' + data.error, 'error');
            }
        } catch (e) { showToast('Import Failed', 'error'); }
        setLoading(false);
    };

    return (
        <div className="space-y-4">
            <div>
                <label className="block text-sm text-gray-400 mb-1">Wallet Type</label>
                <select 
                    value={walletType} 
                    onChange={(e) => setWalletType(e.target.value)}
                    className="w-full bg-gray-900 border border-gray-700 rounded p-2 text-white"
                >
                    <option value="eth">EVM (Ethereum/BSC)</option>
                    <option value="binance">Binance Exchange</option>
                    <option value="kucoin">KuCoin Exchange</option>
                    <option value="bybit">Bybit Exchange</option>
                    <option value="okx">OKX Exchange</option>
                </select>
            </div>
            <div>
                <label className="block text-sm text-gray-400 mb-1">Wallet Name</label>
                <input 
                    type="text" 
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    className="w-full bg-gray-900 border border-gray-700 rounded p-2 text-white"
                />
            </div>
            
            {walletType === 'eth' ? (
                <div>
                    <label className="block text-sm text-gray-400 mb-1">Private Key</label>
                    <input 
                        type="password" 
                        value={privateKey}
                        onChange={(e) => setPrivateKey(e.target.value)}
                        className="w-full bg-gray-900 border border-gray-700 rounded p-2 text-white font-mono text-sm"
                        placeholder="0x..."
                    />
                </div>
            ) : (
                <>
                    <div>
                        <label className="block text-sm text-gray-400 mb-1">API Key</label>
                        <input 
                            type="text" 
                            value={apiKey}
                            onChange={(e) => setApiKey(e.target.value)}
                            className="w-full bg-gray-900 border border-gray-700 rounded p-2 text-white font-mono text-sm"
                        />
                    </div>
                    <div>
                        <label className="block text-sm text-gray-400 mb-1">API Secret</label>
                        <input 
                            type="password" 
                            value={apiSecret}
                            onChange={(e) => setApiSecret(e.target.value)}
                            className="w-full bg-gray-900 border border-gray-700 rounded p-2 text-white font-mono text-sm"
                        />
                    </div>
                </>
            )}

            <button 
                onClick={handleImport} 
                disabled={loading}
                className="bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-2 rounded font-medium disabled:opacity-50 w-full"
            >
                {loading ? 'Importing...' : 'Import Wallet'}
            </button>
        </div>
    );
};

const WalletList = ({ username }: { username: string }) => {
    const [wallets, setWallets] = useState<any[]>([]);
    const [loading, setLoading] = useState(false);
    const [revealKey, setRevealKey] = useState<{address: string, key: string} | null>(null);
    const [password, setPassword] = useState('');
    const [showPasswordPrompt, setShowPasswordPrompt] = useState<{address: string, chain: string} | null>(null);
    const { showToast } = useToast();

    const fetchWallets = async () => {
        try {
            const res = await fetch(`/api/wallet/list?username=${username}`);
            const data = await res.json();
            if (Array.isArray(data)) {
                setWallets(data);
            } else {
                setWallets([]);
            }
        } catch (e) { console.error(e); }
    };

    useEffect(() => {
        fetchWallets();
    }, [username]);

    const handleGenerate = async (chain: string) => {
        setLoading(true);
        try {
            const res = await fetch('/api/wallet/generate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, chain })
            });
            const data = await res.json();
            if (data.address) {
                showToast(`${chain} Wallet Generated!`, 'success');
                fetchWallets();
            } else {
                showToast(`Error: ${data.error}`, 'error');
            }
        } catch (e) { showToast('Generation Failed', 'error'); }
        setLoading(false);
    };

    const handleReveal = async () => {
        if (!showPasswordPrompt || !password) return;
        setLoading(true);
        try {
            const res = await fetch('/api/wallet/reveal', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    username, 
                    chain: showPasswordPrompt.chain, 
                    password 
                })
            });
            const data = await res.json();
            if (data.private_key) {
                setRevealKey({ address: showPasswordPrompt.address, key: data.private_key });
                setShowPasswordPrompt(null);
                setPassword('');
            } else {
                showToast(data.error || 'Invalid Password', 'error');
            }
        } catch (e) { showToast('Failed to reveal key', 'error'); }
        setLoading(false);
    };

    return (
        <div className="space-y-4">
            <div className="flex gap-2 mb-4">
                <button onClick={() => handleGenerate('EVM')} disabled={loading} className="flex-1 bg-blue-600 hover:bg-blue-700 text-white p-2 rounded text-sm font-bold transition">
                    + EVM (ETH/BSC)
                </button>
                <button onClick={() => handleGenerate('TRON')} disabled={loading} className="flex-1 bg-red-600 hover:bg-red-700 text-white p-2 rounded text-sm font-bold transition">
                    + TRON (TRX/USDT)
                </button>
                <button onClick={() => handleGenerate('BTC')} disabled={loading} className="flex-1 bg-orange-600 hover:bg-orange-700 text-white p-2 rounded text-sm font-bold transition">
                    + Bitcoin (BTC)
                </button>
            </div>

            {wallets.length === 0 ? (
                <div className="text-gray-500 italic text-center py-4">No wallets generated yet.</div>
            ) : (
                <div className="space-y-3">
                    {wallets.map((w, i) => (
                        <div key={i} className="bg-gray-900 p-4 rounded border border-gray-700 relative group">
                            <div className="flex justify-between items-start mb-2">
                                <div>
                                    <div className="font-bold text-white flex items-center gap-2">
                                        {w.name} 
                                        <span className="text-[10px] bg-gray-700 px-1.5 rounded text-gray-300">{w.type}</span>
                                    </div>
                                    <div className="text-xs text-gray-500 font-mono mt-1 break-all">{w.address}</div>
                                </div>
                                <button 
                                    onClick={() => setShowPasswordPrompt({ address: w.address, chain: w.type })}
                                    className="text-xs bg-gray-800 hover:bg-gray-700 text-gray-300 px-2 py-1 rounded border border-gray-600 transition"
                                >
                                    Reveal Key
                                </button>
                            </div>
                        </div>
                    ))}
                </div>
            )}

            {/* Password Modal */}
            {showPasswordPrompt && (
                <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4">
                    <div className="bg-gray-800 p-6 rounded-xl border border-gray-700 w-full max-w-sm">
                        <h3 className="font-bold text-white mb-4">Enter Password to Reveal Key</h3>
                        <input 
                            type="password" 
                            value={password}
                            onChange={e => setPassword(e.target.value)}
                            className="w-full bg-gray-900 border border-gray-600 rounded p-2 text-white mb-4"
                            placeholder="Your Password"
                        />
                        <div className="flex gap-2">
                            <button onClick={() => setShowPasswordPrompt(null)} className="flex-1 bg-gray-700 text-white p-2 rounded">Cancel</button>
                            <button onClick={handleReveal} disabled={loading} className="flex-1 bg-indigo-600 text-white p-2 rounded font-bold">
                                {loading ? '...' : 'Confirm'}
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* Key Reveal Modal */}
            {revealKey && (
                <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4">
                    <div className="bg-gray-800 p-6 rounded-xl border border-gray-700 w-full max-w-lg">
                        <h3 className="font-bold text-white mb-2">Private Key Revealed</h3>
                        <p className="text-red-400 text-xs mb-4">WARNING: Never share this key. Anyone with this key can steal your funds.</p>
                        
                        <div className="bg-gray-900 p-3 rounded border border-gray-700 font-mono text-xs text-green-400 break-all mb-4 select-all">
                            {revealKey.key}
                        </div>
                        
                        <button onClick={() => setRevealKey(null)} className="w-full bg-gray-700 hover:bg-gray-600 text-white p-2 rounded font-bold">
                            Close & Clear
                        </button>
                    </div>
                </div>
            )}
        </div>
    );
};



const AutoTradingPanel = () => {
    const [settings, setSettings] = useState<any>(null);
    const [activeTrade, setActiveTrade] = useState<any>(null);
    const [history, setHistory] = useState<any[]>([]);
    const [loading, setLoading] = useState(false);
    const username = getUser();

    const fetchStatus = async () => {
        try {
            const res = await fetch(`/api/bot/status?username=${username}`);
            const data = await res.json();
            setSettings(data.settings);
            setActiveTrade(data.active_trade);
            setHistory(Array.isArray(data.history) ? data.history : []);
        } catch(e) { console.error(e); }
    };

    useEffect(() => {
        fetchStatus();
        const interval = setInterval(fetchStatus, 5000);
        return () => clearInterval(interval);
    }, []);

    const toggleBot = async (enabled: boolean) => {
        setLoading(true);
        try {
            await fetch('/api/bot/toggle', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ username, enabled })
            });
            await fetchStatus();
        } catch(e) { console.error(e); }
        setLoading(false);
    };

    const updateConfig = async (key: string, value: any) => {
        try {
            await fetch('/api/bot/config', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ username, [key]: value })
            });
            fetchStatus();
        } catch(e) { console.error(e); }
    };

    return (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 p-6">
            <div className="lg:col-span-2 space-y-6">
                {/* Status Card */}
                <div className="bg-gray-800 rounded-xl p-6 border border-gray-700">
                    <div className="flex justify-between items-center mb-6">
                        <div>
                            <h2 className="text-2xl font-bold text-white flex items-center gap-2">
                                <Zap className="text-yellow-400" /> Auto Trading Bot
                            </h2>
                            <p className="text-gray-400 text-sm">AI-Powered High Frequency Trading</p>
                        </div>
                        <div className="flex items-center gap-4">
                            <ConnectButton showBalance={false} />
                            <button 
                                onClick={() => toggleBot(!settings?.enabled)}
                                disabled={loading}
                                className={`px-6 py-3 rounded-lg font-bold text-lg shadow-lg transition-all ${
                                    settings?.enabled 
                                    ? 'bg-red-600 hover:bg-red-700 text-white shadow-red-900/20' 
                                    : 'bg-green-600 hover:bg-green-700 text-white shadow-green-900/20'
                                }`}
                            >
                                {loading ? '...' : settings?.enabled ? 'STOP BOT' : 'START BOT'}
                            </button>
                        </div>
                    </div>

                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
                        <div className="bg-gray-900 p-4 rounded-lg border border-gray-700">
                            <div className="text-gray-500 text-xs mb-1">Status</div>
                            <div className={`font-bold ${settings?.is_active ? 'text-green-400' : 'text-gray-400'}`}>
                                {settings?.is_active ? 'RUNNING' : 'STOPPED'}
                            </div>
                        </div>
                        <div className="bg-gray-900 p-4 rounded-lg border border-gray-700">
                            <div className="text-gray-500 text-xs mb-1">Win Rate</div>
                            <div className="font-bold text-indigo-400">76.4%</div>
                        </div>
                        <div className="bg-gray-900 p-4 rounded-lg border border-gray-700">
                            <div className="text-gray-500 text-xs mb-1">Total Profit</div>
                            <div className="font-bold text-green-400">+$1,240.50</div>
                        </div>
                        <div className="bg-gray-900 p-4 rounded-lg border border-gray-700">
                            <div className="text-gray-500 text-xs mb-1">Active Deals</div>
                            <div className="font-bold text-white">{activeTrade ? 1 : 0}</div>
                        </div>
                    </div>

                    {/* Configuration */}
                    <div className="border-t border-gray-700 pt-6">
                        <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                            <Settings size={18} /> Risk Management
                        </h3>
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                            <div>
                                <label className="block text-xs text-gray-400 mb-1">Trade Amount (USDT)</label>
                                <input 
                                    type="number" 
                                    value={settings?.investment_amount || 0}
                                    onChange={(e) => updateConfig('investment_amount', parseFloat(e.target.value))}
                                    className="w-full bg-gray-900 border border-gray-600 rounded p-2 text-white focus:border-indigo-500"
                                />
                            </div>
                            <div>
                                <label className="block text-xs text-gray-400 mb-1">Risk Level</label>
                                <select 
                                    value={settings?.risk_level || 'medium'}
                                    onChange={(e) => updateConfig('risk_level', e.target.value)}
                                    className="w-full bg-gray-900 border border-gray-600 rounded p-2 text-white focus:border-indigo-500"
                                >
                                    <option value="conservative">Conservative (Low Risk)</option>
                                    <option value="medium">Medium (Balanced)</option>
                                    <option value="aggressive">Aggressive (High Risk)</option>
                                </select>
                            </div>
                            <div>
                                <label className="block text-xs text-gray-400 mb-1">Strategy</label>
                                <select 
                                    value={settings?.strategy || 'advanced_ai'}
                                    onChange={(e) => updateConfig('strategy', e.target.value)}
                                    className="w-full bg-gray-900 border border-gray-600 rounded p-2 text-white focus:border-indigo-500"
                                >
                                    <option value="advanced_ai">Advanced AI (Hybrid)</option>
                                    <option value="technical">Technical Analysis</option>
                                    <option value="sentiment">Sentiment Only</option>
                                </select>
                            </div>
                        </div>
                    </div>
                </div>

                {/* Active Trade */}
                {activeTrade && (
                    <div className="bg-indigo-900/20 border border-indigo-500/50 rounded-xl p-6 animate-pulse">
                        <div className="flex justify-between items-start">
                            <div>
                                <div className="text-indigo-400 font-bold mb-1">ACTIVE POSITION</div>
                                <div className="text-2xl font-bold text-white">{activeTrade.symbol}</div>
                                <div className={`text-lg font-bold ${activeTrade.side === 'buy' ? 'text-green-400' : 'text-red-400'}`}>
                                    {activeTrade.side.toUpperCase()}
                                </div>
                            </div>
                            <div className="text-right">
                                <div className="text-gray-400 text-sm">Entry Price</div>
                                <div className="text-xl font-mono text-white">{activeTrade.entry_price}</div>
                                <div className="text-gray-400 text-sm mt-2">Current PNL</div>
                                <div className="text-xl font-mono text-green-400">+0.45%</div>
                            </div>
                        </div>
                    </div>
                )}
            </div>

            <div className="bg-gray-800 rounded-xl border border-gray-700 flex flex-col h-[600px]">
                <div className="p-4 border-b border-gray-700 font-bold text-white flex items-center gap-2">
                    <History size={18} /> Trade History
                </div>
                <div className="flex-1 overflow-auto p-2">
                    {history.length > 0 ? history.map((h, i) => (
                        <div key={i} className="bg-gray-900 p-3 rounded mb-2 border border-gray-700/50 hover:border-gray-600 transition">
                            <div className="flex justify-between mb-1">
                                <span className="font-bold text-white">{h.symbol}</span>
                                <span className="text-xs text-gray-500">{new Date(h.timestamp * 1000).toLocaleTimeString()}</span>
                            </div>
                            <div className="flex justify-between text-sm">
                                <span className={h.profit >= 0 ? 'text-green-400' : 'text-red-400'}>
                                    {h.profit >= 0 ? '+' : ''}{Number(h.profit).toFixed(2)} USDT
                                </span>
                                <span className={`uppercase text-xs px-1.5 py-0.5 rounded ${h.side === 'buy' ? 'bg-green-900/50 text-green-400' : 'bg-red-900/50 text-red-400'}`}>
                                    {h.side}
                                </span>
                            </div>
                        </div>
                    )) : (
                        <div className="text-center text-gray-500 mt-10">No trades yet</div>
                    )}
                </div>
            </div>
        </div>
    );
};

// --- DeFi Module ---

const ArbitrageScanner = () => {
    const [opportunities, setOpportunities] = useState<any[]>([]);
    const [loading, setLoading] = useState(false);

    const scanArbitrage = async () => {
        setLoading(true);
        const pairs = ['ETH', 'BTC', 'SOL', 'BNB'];
        const results = [];
        for (const p of pairs) {
            try {
                const res = await fetch(`/api/web3/arbitrage?symbol=${p}`);
                const data = await res.json();
                results.push(data);
            } catch (e) { console.error(e); }
        }
        setOpportunities(results);
        setLoading(false);
    };

    return (
        <div className="bg-gray-800 p-6 rounded-xl border border-gray-700 mt-6">
            <div className="flex justify-between items-center mb-4">
                <h3 className="text-xl font-bold text-white flex items-center gap-2">
                    <Activity className="text-indigo-400" /> Web3 Arbitrage Scanner
                </h3>
                <button onClick={scanArbitrage} disabled={loading} className="bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-2 rounded font-bold text-sm">
                    {loading ? 'Scanning DEX/CEX...' : 'Scan Opportunities'}
                </button>
            </div>
            
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
                {opportunities.map((opp, i) => (
                    <div key={i} className={`p-4 rounded border ${opp.opportunity ? 'bg-green-900/20 border-green-500/50' : 'bg-gray-900 border-gray-800'}`}>
                        <div className="flex justify-between items-center mb-2">
                            <span className="font-bold text-white">{opp.symbol}</span>
                            <span className={`text-xs font-bold px-2 py-0.5 rounded ${opp.opportunity ? 'bg-green-900 text-green-400' : 'bg-gray-800 text-gray-500'}`}>
                                {opp.opportunity ? 'OPPORTUNITY' : 'NO SPREAD'}
                            </span>
                        </div>
                        <div className="space-y-1 text-sm">
                            <div className="flex justify-between text-gray-400">
                                <span>CEX Price:</span>
                                <span className="text-white">{formatMoney(opp.cex_price)}</span>
                            </div>
                            <div className="flex justify-between text-gray-400">
                                <span>DEX Price:</span>
                                <span className="text-white">{formatMoney(opp.dex_price)}</span>
                            </div>
                            <div className="flex justify-between text-gray-400 font-bold pt-2 border-t border-gray-700 mt-2">
                                <span>Spread:</span>
                                <span className={opp.difference_pct > 0 ? 'text-green-400' : 'text-red-400'}>
                                    {opp.difference_pct !== undefined ? Number(opp.difference_pct).toFixed(2) : '0.00'}%
                                </span>
                            </div>
                            {opp.opportunity && (
                                <div className="text-xs text-green-300 mt-2 italic">
                                    {opp.direction}
                                </div>
                            )}
                        </div>
                    </div>
                ))}
                {opportunities.length === 0 && !loading && (
                    <div className="col-span-full text-center text-gray-500 py-8">Click Scan to find arbitrage opportunities across CEX and DEX.</div>
                )}
            </div>
        </div>
    );
};

const CopyTradingModule = () => {
    const [traders, setTraders] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);
    const { showToast } = useToast();
    
    useEffect(() => {
        fetch('/api/copy-trade/traders')
            .then(res => res.json())
            .then(data => {
                setTraders(data);
                setLoading(false);
            })
            .catch(err => {
                console.error(err);
                setLoading(false);
            });
    }, []);

    const handleFollow = async (traderId: number, name: string) => {
        const username = getUser();
        // Removed intrusive confirm
        showToast(`Initiating copy trade for ${name}...`, 'info');
        
        try {
            const res = await fetch('/api/copy-trade/follow', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ username, trader_id: traderId })
            });
            const data = await res.json();
            if(data.status === 'success') showToast(data.message, 'success');
            else showToast(data.error, 'error');
        } catch(e) { showToast('Failed to follow trader', 'error'); }
    };

    return (
        <div className="p-6 h-full overflow-y-auto">
            <div className="max-w-6xl mx-auto">
                <h2 className="text-2xl font-bold text-white flex items-center gap-2 mb-6">
                    <History className="text-indigo-400" /> Copy Trading
                </h2>
                
                {loading ? (
                    <div className="text-center text-gray-500">Loading Top Traders...</div>
                ) : (
                    <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
                        {traders.map(trader => (
                            <div key={trader.id} className="bg-gray-800 rounded-xl p-6 border border-gray-700 hover:border-indigo-500 transition cursor-pointer relative overflow-hidden group">
                                <div className="absolute top-0 right-0 p-2 bg-gray-900 rounded-bl-lg text-xs font-bold text-gray-400">
                                    {trader.risk} Risk
                                </div>
                                
                                <div className="flex items-center gap-4 mb-4">
                                    <div className="w-12 h-12 rounded-full bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center text-xl font-bold text-white">
                                        {trader.name[0]}
                                    </div>
                                    <div>
                                        <div className="font-bold text-white text-lg">{trader.name}</div>
                                        <div className="text-xs text-gray-500">{trader.followers.toLocaleString()} followers</div>
                                    </div>
                                </div>
                                
                                <div className="grid grid-cols-2 gap-4 mb-6">
                                    <div className="bg-gray-900/50 p-3 rounded-lg">
                                        <div className="text-xs text-gray-500 mb-1">Total PNL</div>
                                        <div className="text-green-400 font-bold text-lg">+{trader.pnl}%</div>
                                    </div>
                                    <div className="bg-gray-900/50 p-3 rounded-lg">
                                        <div className="text-xs text-gray-500 mb-1">Win Rate</div>
                                        <div className="text-indigo-400 font-bold text-lg">{trader.winRate}%</div>
                                    </div>
                                </div>
                                
                                <button 
                                    onClick={() => handleFollow(trader.id, trader.name)}
                                    className="w-full bg-indigo-600 hover:bg-indigo-700 text-white font-bold py-2 rounded transition"
                                >
                                    Copy Strategy
                                </button>
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
};

const CryptoWithdrawalForm = ({ username, onSuccess }: { username: string, onSuccess: () => void }) => {
    const [amount, setAmount] = useState('');
    const [address, setAddress] = useState('');
    const [currency, setCurrency] = useState('USDT');
    const [chain, setChain] = useState('EVM');
    const [password, setPassword] = useState('');
    const [loading, setLoading] = useState(false);
    const { showToast } = useToast();

    const handleWithdraw = async () => {
        if (!amount || !address || !password) return showToast("Fill all fields including password", 'warning');
        setLoading(true);
        try {
            const res = await fetch('/api/wallet/transfer', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ 
                    username, 
                    chain, 
                    currency, 
                    amount: parseFloat(amount), 
                    to_address: address,
                    password
                })
            });
            const data = await res.json();
            if (data.tx_hash || data.status === 'success') {
                showToast(`Transfer Sent! TX: ${data.tx_hash || 'Pending'}`, 'success');
                setAmount('');
                setAddress('');
                setPassword('');
                onSuccess();
            }
            else showToast("Failed: " + (data.error || 'Unknown Error'), 'error');
        } catch (e) { showToast("Error processing withdrawal", 'error'); }
        setLoading(false);
    };

    return (
        <div className="space-y-3">
            <div className="flex gap-2">
                <select 
                    value={chain} 
                    onChange={e => setChain(e.target.value)}
                    className="bg-gray-900 border border-gray-600 rounded p-2 text-white text-xs"
                >
                    <option value="EVM">EVM (ETH/BSC)</option>
                    <option value="TRON">TRON</option>
                    <option value="BTC">Bitcoin</option>
                </select>
                <select 
                    value={currency} 
                    onChange={e => setCurrency(e.target.value)}
                    className="bg-gray-900 border border-gray-600 rounded p-2 text-white flex-1"
                >
                    <option value="USDT">USDT</option>
                    <option value="BTC">BTC</option>
                    <option value="ETH">ETH</option>
                    <option value="BNB">BNB</option>
                    <option value="TRX">TRX</option>
                </select>
            </div>
            <input 
                type="number" 
                placeholder="Amount" 
                className="w-full bg-gray-900 p-2 rounded text-white border border-gray-600" 
                value={amount} 
                onChange={e => setAmount(e.target.value)} 
            />
            <input 
                type="text" 
                placeholder="Recipient Address (0x... or T...)" 
                className="w-full bg-gray-900 p-2 rounded text-white border border-gray-600 font-mono text-sm" 
                value={address} 
                onChange={e => setAddress(e.target.value)} 
            />
            <input 
                type="password" 
                placeholder="Account Password (Required)" 
                className="w-full bg-gray-900 p-2 rounded text-white border border-gray-600" 
                value={password} 
                onChange={e => setPassword(e.target.value)} 
            />
            <button onClick={handleWithdraw} disabled={loading} className="w-full bg-indigo-600 hover:bg-indigo-700 text-white p-2 rounded font-bold transition">
                {loading ? 'Processing...' : 'Send Crypto'}
            </button>
        </div>
    );
};

// Embedded version of DeFi Module for the Funds page
const DeFiModuleEmbedded = ({ onSuccess }: { onSuccess?: () => void }) => {
    const [fromToken, setFromToken] = useState('NGN');
    const [toToken, setToToken] = useState('USDT');
    const [amount, setAmount] = useState('');
    const [loading, setLoading] = useState(false);
    const { showToast } = useToast();

    const handleSwap = async () => {
        if (!amount) return;
        setLoading(true);
        try {
            const res = await fetch('/api/swap', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    username: getUser(),
                    amount: parseFloat(amount),
                    from_currency: fromToken,
                    to_currency: toToken
                })
            });
            const data = await res.json();
            if (data.status === 'success') {
                showToast(data.message, 'success');
                setAmount('');
                if (onSuccess) onSuccess();
            } else {
                showToast('Swap Failed: ' + data.error, 'error');
            }
        } catch (e) { console.error(e); }
        setLoading(false);
    };

    return (
        <div className="flex flex-col md:flex-row gap-4 items-center">
             <div className="flex-1 flex gap-2 w-full">
                <input type="number" value={amount} onChange={e => setAmount(e.target.value)} placeholder="Amount" className="flex-1 bg-gray-900 p-2 rounded text-white border border-gray-600" />
                <select value={fromToken} onChange={e => setFromToken(e.target.value)} className="bg-gray-900 text-white p-2 rounded border border-gray-600">
                    <option value="NGN">NGN</option>
                    <option value="USDT">USDT</option>
                </select>
             </div>
             <ArrowDown className="text-gray-400 rotate-0 md:-rotate-90" />
             <div className="flex-1 flex gap-2 w-full">
                <select value={toToken} onChange={e => setToToken(e.target.value)} className="bg-gray-900 text-white p-2 rounded border border-gray-600 w-full">
                    <option value="USDT">USDT</option>
                    <option value="NGN">NGN</option>
                    <option value="BTC">BTC</option>
                </select>
             </div>
             <button onClick={handleSwap} disabled={loading} className="w-full md:w-auto bg-indigo-600 px-6 py-2 rounded text-white font-bold">Swap</button>
        </div>
    );
};

const FundsManager = ({ balances, onRefresh }: { balances: Balances | null, onRefresh: () => void }) => {
    // Balances are now passed from parent
    const [depositProvider, setDepositProvider] = useState('flutterwave');
    const [showImportWallet, setShowImportWallet] = useState(false);
    const username = getUser();

    // fetchBalances and internal interval removed in favor of parent state


    const [depositAmount, setDepositAmount] = useState('');
    const [paymentResult, setPaymentResult] = useState<any>(null);
    const [depositError, setDepositError] = useState('');

    const handleDeposit = async () => {
        setPaymentResult(null);
        setDepositError('');
        
        if(!depositAmount) return;
        const amount = parseFloat(depositAmount);
        if(amount <= 0) {
            setDepositError("Invalid amount");
            return;
        }

        try {
            const res = await fetch(`/api/${depositProvider}/pay`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ 
                    amount, 
                    email: getUserEmail(), 
                    username: username 
                })
            });
            const data = await res.json();
            if(data.status === 'success' && data.link) {
                setPaymentResult(data);
                setDepositAmount('');
            } else {
                setDepositError("Failed to create payment: " + (data.message || data.error));
            }
        } catch(e) {
            setDepositError("Network Error");
        }
    };

    return (
        <div className="p-6 space-y-6 h-full overflow-y-auto">
            <h2 className="text-2xl font-bold text-white flex items-center gap-2">
                <Wallet className="text-indigo-400" /> Funds & Wallets
            </h2>

            {/* Balances */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                {['NGN', 'USDT', 'BTC', 'ETH'].map(curr => (
                    <div key={curr} className="bg-gray-800 p-4 rounded-xl border border-gray-700">
                        <div className="text-gray-500 text-xs mb-1">{curr} Balance</div>
                        <div className="text-2xl font-bold text-white">
                            {curr === 'NGN' ? '₦' : ''}{typeof balances?.[curr as keyof Balances] === 'number' ? balances[curr as keyof Balances].toLocaleString() : '0.00'}
                        </div>
                    </div>
                ))}
            </div>

            {/* Wallet Management Section */}
            <div className="grid md:grid-cols-2 gap-6">
                 <div className="space-y-6">
                    {/* Connected Wallets */}
                    <div className="bg-gray-800 p-6 rounded-xl border border-gray-700">
                        <div className="flex justify-between items-center mb-4">
                            <h3 className="font-bold text-white flex items-center gap-2">
                                <Wallet size={18} className="text-blue-400" /> Connected Wallets
                            </h3>
                            <button 
                                onClick={() => setShowImportWallet(!showImportWallet)}
                                className="text-xs bg-indigo-600 hover:bg-indigo-700 text-white px-3 py-1 rounded"
                            >
                                {showImportWallet ? 'Cancel Import' : 'Import Wallet'}
                            </button>
                        </div>
                        
                        {showImportWallet ? (
                            <div className="bg-gray-900 p-4 rounded border border-gray-700 mb-4">
                                <ImportWalletForm username={username} onImport={() => setShowImportWallet(false)} />
                            </div>
                        ) : null}

                        <WalletList username={username} />
                    </div>

                    {/* Deposit Management */}
                    <div className="bg-gray-800 p-6 rounded-xl border border-gray-700">
                        <h3 className="font-bold text-white mb-4 flex items-center gap-2">
                            <ArrowDown size={18} className="text-green-400" /> Deposit Funds
                        </h3>
                        <p className="text-sm text-gray-400 mb-4">
                            Select provider to deposit funds.
                        </p>
                        
                        <div className="space-y-3">
                            <select 
                                value={depositProvider} 
                                onChange={(e) => setDepositProvider(e.target.value)}
                                className="w-full bg-gray-900 text-white p-3 rounded border border-gray-600"
                            >
                                <option value="flutterwave">Flutterwave (NGN - Card/Bank)</option>
                                <option value="paystack">Paystack (NGN - Card/USSD)</option>
                                <option value="stripe">Stripe (USD/Global Card)</option>
                            </select>

                            <input 
                                type="number" 
                                value={depositAmount} 
                                onChange={(e) => setDepositAmount(e.target.value)} 
                                placeholder="Amount (e.g. 5000)" 
                                className="w-full bg-gray-900 text-white p-3 rounded border border-gray-600"
                            />
                            
                            {depositError && (
                                <div className="text-red-500 text-sm p-2 bg-red-900/20 rounded">
                                    {depositError}
                                </div>
                            )}

                            {paymentResult && (
                                <div className="text-green-500 text-sm p-2 bg-green-900/20 rounded">
                                    <p>Payment Created!</p>
                                    <a href={paymentResult.link} target="_blank" rel="noopener noreferrer" className="underline font-bold">
                                        Click here to pay
                                    </a>
                                </div>
                            )}

                            <button 
                                onClick={handleDeposit}
                                className="w-full bg-green-600 hover:bg-green-700 text-white py-3 rounded font-bold"
                            >
                                Deposit with {depositProvider.charAt(0).toUpperCase() + depositProvider.slice(1)}
                            </button>
                        </div>

 
                    </div>
                 </div>

                 <div className="space-y-6">
                     <WithdrawalForm username={username} />
                     
                    {/* Crypto Management */}
                    <div className="bg-gray-800 p-6 rounded-xl border border-gray-700">
                        <h3 className="font-bold text-white mb-4 flex items-center gap-2">
                            <LogOut size={18} className="text-orange-400" /> Withdraw Crypto
                        </h3>
                        <CryptoWithdrawalForm username={username} onSuccess={onRefresh} />
                    </div>

                    {/* Swap Section Reuse */}
                     <div className="bg-gray-800 p-6 rounded-xl border border-gray-700">
                        <h3 className="font-bold text-white mb-4">Quick Swap (NGN ↔ USDT)</h3>
                        <DeFiModuleEmbedded onSuccess={onRefresh} />
                    </div>
                </div>
            </div>
        </div>
    );
};

const DeFiModule = ({ balances, onSuccess }: { balances: Balances | null, onSuccess?: () => void }) => {
    const [fromToken, setFromToken] = useState('ETH');
    const [toToken, setToToken] = useState('USDT');
    const [amount, setAmount] = useState('');
    const [loading, setLoading] = useState(false);
    const [rate, setRate] = useState<number | null>(null);
    const { showToast } = useToast();

    useEffect(() => {
        const fetchRate = async () => {
            try {
                // Determine symbol for rate fetch
                let symbol = `${fromToken}/${toToken}`;
                // Handle specific pairs or reverse if needed, or rely on api_ticker's logic
                // For simplicity, try direct pair first
                const res = await fetch(`/api/ticker?symbol=${symbol}`);
                const data = await res.json();
                if (data.last) {
                    setRate(data.last);
                } else {
                    // Try reverse
                     const resRev = await fetch(`/api/ticker?symbol=${toToken}/${fromToken}`);
                     const dataRev = await resRev.json();
                     if (dataRev.last) setRate(1 / dataRev.last);
                }
            } catch (e) { console.error(e); }
        };
        fetchRate();
        const interval = setInterval(fetchRate, 10000);
        return () => clearInterval(interval);
    }, [fromToken, toToken]);

    const handleSwap = async () => {
        if (!amount) return;
        setLoading(true);
        
        try {
            const res = await fetch('/api/swap', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    username: getUser(),
                    amount: parseFloat(amount),
                    from_currency: fromToken,
                    to_currency: toToken
                })
            });
            const data = await res.json();
            
            if (data.status === 'success') {
                showToast(data.message, 'success');
                setAmount('');
                if (onSuccess) onSuccess();
            } else {
                showToast('Swap Failed: ' + data.error, 'error');
            }
        } catch (e) {
            console.error(e);
            showToast('Swap Error', 'error');
        }
        setLoading(false);
    };

    return (
        <div className="p-6 h-full overflow-y-auto flex justify-center items-center">
            <div className="bg-gray-800 rounded-xl p-8 border border-gray-700 w-full max-w-md shadow-2xl">
                <h2 className="text-2xl font-bold text-white mb-6 flex items-center gap-2">
                    <Layers className="text-indigo-400" /> DeFi Swap
                </h2>
                
                <div className="space-y-4">
                    <div className="bg-gray-900 p-4 rounded-lg border border-gray-700">
                        <div className="flex justify-between mb-2">
                            <span className="text-gray-400 text-sm">From</span>
                            <span className="text-gray-400 text-sm">Balance: {typeof balances?.[fromToken as keyof Balances] === 'number' ? balances[fromToken as keyof Balances].toFixed(6) : '0.00'}</span>
                        </div>
                        <div className="flex gap-2">
                            <input 
                                type="number" 
                                value={amount}
                                onChange={(e) => setAmount(e.target.value)}
                                placeholder="0.00"
                                className="bg-transparent text-2xl font-bold text-white outline-none w-full"
                            />
                            <select 
                                value={fromToken}
                                onChange={(e) => setFromToken(e.target.value)}
                                className="bg-gray-800 text-white rounded px-2 py-1 outline-none border border-gray-700 font-bold"
                            >
                                <option value="ETH">ETH</option>
                                <option value="USDT">USDT</option>
                                <option value="BTC">BTC</option>
                                <option value="BNB">BNB</option>
                                <option value="NGN">NGN</option>
                            </select>
                        </div>
                    </div>

                    <div className="flex justify-center">
                        <div className="bg-gray-700 p-2 rounded-full border border-gray-600">
                            <ArrowDown size={20} className="text-gray-300" />
                        </div>
                    </div>

                    <div className="bg-gray-900 p-4 rounded-lg border border-gray-700">
                        <div className="flex justify-between mb-2">
                            <span className="text-gray-400 text-sm">To</span>
                            <span className="text-gray-400 text-sm">Balance: 0.00</span>
                        </div>
                        <div className="flex gap-2">
                            <input 
                                type="number" 
                                value={amount && rate ? (parseFloat(amount) * rate).toFixed(6) : ''} 
                                readOnly
                                placeholder="0.00"
                                className="bg-transparent text-2xl font-bold text-white outline-none w-full"
                            />
                            <select 
                                value={toToken}
                                onChange={(e) => setToToken(e.target.value)}
                                className="bg-gray-800 text-white rounded px-2 py-1 outline-none border border-gray-700 font-bold"
                            >
                                <option value="USDT">USDT</option>
                                <option value="ETH">ETH</option>
                                <option value="BTC">BTC</option>
                                <option value="DAI">DAI</option>
                                <option value="NGN">NGN</option>
                            </select>
                        </div>
                    </div>

                    <div className="pt-4">
                        <div className="flex justify-between text-sm text-gray-500 mb-2">
                            <span>Rate</span>
                            <span>1 {fromToken} = {rate ? rate.toFixed(6) : '...'} {toToken}</span>
                        </div>
                        <div className="flex justify-between text-sm text-gray-500 mb-4">
                            <span>Network Fee</span>
                            <span>$4.50</span>
                        </div>
                        
                        <button 
                            onClick={handleSwap}
                            disabled={loading || !amount}
                            className="w-full bg-indigo-600 hover:bg-indigo-700 text-white font-bold py-4 rounded-lg transition disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                            {loading ? 'Swapping...' : 'Swap Tokens'}
                        </button>
                    </div>
                </div>
            </div>
            
            <ArbitrageScanner />
        </div>
    );
};

const TradePanel = ({ 
    symbol, 
    candles,
    balance,
    onPlaceOrder,
    onDeposit,
    onSwap
}: { 
    symbol: string, 
    candles: Candle[],
    balance: number,
    onPlaceOrder: (order: any) => void,
    onDeposit: () => void,
    onSwap: () => void
}) => {
    const [amount, setAmount] = useState('');
    const [side, setSide] = useState<'buy' | 'sell'>('buy');
    const [inputType, setInputType] = useState<'amount' | 'total'>('total');
    const [stopLoss, setStopLoss] = useState('');
    const [takeProfit, setTakeProfit] = useState('');
    const [leverage, setLeverage] = useState('1');

    const handleAction = () => {
        if (!amount) return;
        let finalAmount = parseFloat(amount);
        
        // If input is in USDT (Total), convert to Base Currency (e.g. BTC)
        if (inputType === 'total' && candles.length > 0) {
            const price = candles[candles.length - 1].close;
            if (price > 0) {
                finalAmount = finalAmount / price;
            }
        }

        onPlaceOrder({
            side,
            amount: finalAmount,
            stopLoss: stopLoss ? parseFloat(stopLoss) : null,
            takeProfit: takeProfit ? parseFloat(takeProfit) : null,
            leverage: parseFloat(leverage),
            type: 'market'
        });
        
        // Reset form
        setAmount('');
    };

    const currentPrice = candles.length > 0 ? candles[candles.length - 1].close : 0;
    const baseSymbol = symbol.split('/')[0];
    const quoteSymbol = symbol.split('/')[1] || 'USDT';

    return (
        <div className="flex-1 p-4 flex flex-col gap-4 h-full overflow-y-auto">
                <div className="flex bg-gray-900 p-1 rounded border border-gray-800">
                    <button 
                        onClick={() => setSide('buy')}
                        className={`flex-1 py-2 rounded text-sm font-bold transition ${side === 'buy' ? 'bg-green-600 text-white' : 'text-gray-500 hover:text-gray-300'}`}
                    >
                        BUY
                    </button>
                    <button 
                        onClick={() => setSide('sell')}
                        className={`flex-1 py-2 rounded text-sm font-bold transition ${side === 'sell' ? 'bg-red-600 text-white' : 'text-gray-500 hover:text-gray-300'}`}
                    >
                        SELL
                    </button>
                </div>

                <div className="space-y-3">
                    <div>
                        <div className="flex justify-between text-xs text-gray-400 mb-1">
                            <span>Available</span>
                            <span>{balance.toFixed(2)} {quoteSymbol}</span>
                        </div>
                        <label className="text-xs text-gray-500 mb-1 block">Price</label>
                        <div className="bg-gray-900 border border-gray-700 rounded px-3 py-2 text-gray-400 text-sm">
                            {currentPrice > 0 ? formatMoney(currentPrice) : 'Market Price'}
                        </div>
                    </div>
                    
                    <div>
                        <div className="flex justify-between items-center mb-1">
                            <label className="text-xs text-gray-500">
                                {inputType === 'total' ? `Amount (${quoteSymbol})` : `Amount (${baseSymbol})`}
                            </label>
                            <button 
                                onClick={() => setInputType(inputType === 'total' ? 'amount' : 'total')}
                                className="text-[10px] text-indigo-400 hover:text-indigo-300 uppercase font-bold"
                            >
                                Switch to {inputType === 'total' ? 'Lots' : quoteSymbol}
                            </button>
                        </div>
                        <input 
                            type="number" 
                            value={amount}
                            onChange={(e) => setAmount(e.target.value)}
                            className="w-full bg-gray-900 border border-gray-700 rounded px-3 py-2 text-white focus:border-indigo-500 focus:outline-none transition"
                            placeholder={inputType === 'total' ? `0.00 ${quoteSymbol}` : `0.00 ${baseSymbol}`}
                        />
                        {amount && inputType === 'total' && currentPrice > 0 && (
                            <div className="text-[10px] text-gray-500 text-right mt-1">
                                ≈ {(parseFloat(amount) / currentPrice).toFixed(6)} {baseSymbol}
                            </div>
                        )}
                        {amount && inputType === 'amount' && currentPrice > 0 && (
                            <div className="text-[10px] text-gray-500 text-right mt-1">
                                ≈ {formatMoney(parseFloat(amount) * currentPrice)}
                            </div>
                        )}
                    </div>

                    <div className="grid grid-cols-2 gap-2">
                        <div>
                            <label className="text-xs text-gray-500 mb-1 block">Stop Loss</label>
                            <input 
                                type="number" 
                                value={stopLoss}
                                onChange={(e) => setStopLoss(e.target.value)}
                                placeholder="Price"
                                className="w-full bg-gray-900 border border-gray-700 rounded px-2 py-2 text-white text-xs focus:border-indigo-500 focus:outline-none"
                            />
                        </div>
                        <div>
                            <label className="text-xs text-gray-500 mb-1 block">Take Profit</label>
                            <input 
                                type="number" 
                                value={takeProfit}
                                onChange={(e) => setTakeProfit(e.target.value)}
                                placeholder="Price"
                                className="w-full bg-gray-900 border border-gray-700 rounded px-2 py-2 text-white text-xs focus:border-indigo-500 focus:outline-none"
                            />
                        </div>
                    </div>
                    
                    <div>
                        <label className="text-xs text-gray-500 mb-1 block">Leverage</label>
                        <select 
                            value={leverage}
                            onChange={(e) => setLeverage(e.target.value)}
                            className="w-full bg-gray-900 border border-gray-700 rounded px-3 py-2 text-white text-sm focus:border-indigo-500 focus:outline-none"
                        >
                            <option value="1">1x</option>
                            <option value="5">5x</option>
                            <option value="10">10x</option>
                            <option value="20">20x</option>
                        </select>
                    </div>
                </div>

                <button 
                    onClick={handleAction}
                    className={`w-full py-3 rounded font-bold text-white shadow-lg transition transform active:scale-95 ${
                        side === 'buy' 
                        ? 'bg-gradient-to-r from-green-600 to-green-500 hover:from-green-500 hover:to-green-400 shadow-green-900/30' 
                        : 'bg-gradient-to-r from-red-600 to-red-500 hover:from-red-500 hover:to-red-400 shadow-red-900/30'
                    }`}
                >
                    {side === 'buy' ? 'Buy / Long' : 'Sell / Short'} {baseSymbol}
                </button>
                
                <div className="mt-auto pt-4 border-t border-gray-800 grid grid-cols-2 gap-2">
                     <button onClick={onDeposit} className="bg-gray-800 hover:bg-gray-700 text-gray-300 py-2 rounded text-xs font-medium">Deposit</button>
                     <button onClick={onSwap} className="bg-indigo-900/30 hover:bg-indigo-900/50 text-indigo-400 py-2 rounded text-xs font-medium border border-indigo-900">Swap</button>
                </div>
        </div>
    );
};

// --- Advanced Analytics ---

const AdvancedAnalytics = ({ symbol }: { symbol: string }) => {
    const [obAnalysis, setObAnalysis] = useState<any>(null);
    const [riskMetrics, setRiskMetrics] = useState<any>(null);
    const [heatScore, setHeatScore] = useState<any>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchData = async () => {
            // setLoading(true); // Don't flicker on refresh
            try {
                const [obRes, riskRes, heatRes] = await Promise.all([
                    fetch(`/api/analytics/orderbook/${encodeURIComponent(symbol)}`),
                    fetch('/api/analytics/risk'),
                    fetch(`/api/analytics/heat/${encodeURIComponent(symbol)}`)
                ]);
                
                if (obRes.ok) setObAnalysis(await obRes.json());
                if (riskRes.ok) setRiskMetrics(await riskRes.json());
                if (heatRes.ok) setHeatScore(await heatRes.json());
            } catch (e) { console.error(e); }
            setLoading(false);
        };
        
        fetchData();
        const interval = setInterval(fetchData, 10000);
        return () => clearInterval(interval);
    }, [symbol]);

    if (loading && !obAnalysis) return <div className="p-8 text-center text-gray-500">Loading Analytics...</div>;

    return (
        <div className="p-6 h-full overflow-y-auto space-y-6">
            <h2 className="text-2xl font-bold text-white flex items-center gap-2">
                <Activity className="text-purple-400" /> Advanced Analytics
            </h2>
            
            <div className="grid md:grid-cols-3 gap-6">
                {/* Market Heat */}
                <div className="bg-gray-800 p-6 rounded-xl border border-gray-700">
                    <h3 className="text-lg font-bold text-white mb-4">Market Heat</h3>
                    <div className="flex items-center justify-center mb-4">
                        <div className={`w-24 h-24 rounded-full flex items-center justify-center text-3xl font-bold border-4 ${
                            (heatScore?.score || 0) > 70 ? 'border-red-500 text-red-500' : 
                            (heatScore?.score || 0) > 30 ? 'border-yellow-500 text-yellow-500' : 'border-blue-500 text-blue-500'
                        }`}>
                            {Math.round(heatScore?.score || 0)}
                        </div>
                    </div>
                    <div className="text-center text-gray-400 text-sm">
                        Volatility & Momentum Score
                    </div>
                </div>

                {/* Risk Metrics */}
                <div className="bg-gray-800 p-6 rounded-xl border border-gray-700">
                    <h3 className="text-lg font-bold text-white mb-4">Portfolio Risk</h3>
                    <div className="space-y-4">
                        <div className="flex justify-between">
                            <span className="text-gray-400">Sharpe Ratio</span>
                            <span className="font-mono text-white">{riskMetrics?.sharpe_ratio != null ? riskMetrics.sharpe_ratio.toFixed(2) : '0.00'}</span>
                        </div>
                        <div className="flex justify-between">
                            <span className="text-gray-400">Max Drawdown</span>
                            <span className="font-mono text-red-400">{riskMetrics?.max_drawdown != null ? riskMetrics.max_drawdown.toFixed(2) : '0.00'}%</span>
                        </div>
                        <div className="flex justify-between">
                            <span className="text-gray-400">Win Rate</span>
                            <span className="font-mono text-green-400">{riskMetrics?.win_rate != null ? (riskMetrics.win_rate * 100).toFixed(1) : '0.0'}%</span>
                        </div>
                         <div className="flex justify-between">
                            <span className="text-gray-400">Total PnL</span>
                            <span className={`font-mono ${riskMetrics?.total_pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                                {formatMoney(riskMetrics?.total_pnl || 0)}
                            </span>
                        </div>
                    </div>
                </div>

                {/* Order Book Sentiment */}
                <div className="bg-gray-800 p-6 rounded-xl border border-gray-700">
                    <h3 className="text-lg font-bold text-white mb-4">Order Book Analysis</h3>
                    <div className="space-y-4">
                        <div className="flex justify-between">
                            <span className="text-gray-400">Sentiment</span>
                            <span className={`font-bold uppercase ${
                                obAnalysis?.analysis?.sentiment === 'bullish' ? 'text-green-400' : 
                                obAnalysis?.analysis?.sentiment === 'bearish' ? 'text-red-400' : 'text-gray-400'
                            }`}>{obAnalysis?.analysis?.sentiment || 'Neutral'}</span>
                        </div>
                         <div className="flex justify-between">
                            <span className="text-gray-400">Spread</span>
                            <span className="font-mono text-white">{obAnalysis?.analysis?.spread != null ? obAnalysis.analysis.spread.toFixed(2) : '0.00'}</span>
                        </div>
                        <div className="flex justify-between">
                            <span className="text-gray-400">Imbalance</span>
                            <span className="font-mono text-white">{obAnalysis?.analysis?.imbalance_ratio != null ? obAnalysis.analysis.imbalance_ratio.toFixed(2) : '0.00'}</span>
                        </div>
                        <div className="mt-4 p-3 bg-gray-900 rounded text-xs text-gray-400">
                            {obAnalysis?.analysis?.buy_wall ? '🚀 Buy Wall Detected' : obAnalysis?.analysis?.sell_wall ? '📉 Sell Wall Detected' : 'No significant walls'}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
};

// --- Main Dashboard Component ---

export default function Dashboard({ initialView = 'dashboard' }: { initialView?: string }) {
  const [candles, setCandles] = useState<Candle[]>([]);
  const [orderBook, setOrderBook] = useState<OrderBookData | null>(null);
  const [myOrders, setMyOrders] = useState<MyOrder[]>([]);
  const [balances, setBalances] = useState<Balances | null>(null);
  const [activeView, setActiveView] = useState(initialView);
  const [selectedPair, setSelectedPair] = useState('BTC/USDT');
  const [availablePairs, setAvailablePairs] = useState<string[]>([]);
  const [timeframe, setTimeframe] = useState('1m');
  const [chartType, setChartType] = useState<'candle' | 'area'>('area'); // Default to Area
  const [mode, setMode] = useState<'live' | 'demo'>('live'); // Live vs Demo
  const [theme, setTheme] = useState<'light' | 'dark'>('dark'); // Theme State
  const { showToast } = useToast();

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const status = params.get('status');
    const tx_ref = params.get('tx_ref');
    const transaction_id = params.get('transaction_id');
    
    if (status === 'successful' || status === 'success') {
        if (tx_ref || transaction_id) {
            const verifyPayment = async () => {
                try {
                    showToast('Verifying payment...', 'info');
                    const res = await fetch('/api/flutterwave/verify', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({ 
                            username, 
                            tx_ref: tx_ref,
                            transaction_id: transaction_id 
                        })
                    });
                    const data = await res.json();
                    if (data.status === 'success') {
                        showToast(data.message, 'success');
                        fetchUserData();
                        // Clear URL params
                        window.history.replaceState({}, document.title, window.location.pathname);
                        setActiveView('wallet');
                    } else {
                        showToast('Verification Failed: ' + data.error, 'error');
                        // Optional: Clear params even on failure to avoid loops, but maybe user wants to retry?
                        // Usually failure means backend rejected it, so retry with same params is futile.
                        window.history.replaceState({}, document.title, window.location.pathname);
                    }
                } catch (e) {
                    showToast('Verification Network Error', 'error');
                }
            };
            verifyPayment();
        }
    } else if (status === 'cancelled') {
        showToast('Payment Cancelled', 'info');
        window.history.replaceState({}, document.title, window.location.pathname);
    }
  }, []);

  useEffect(() => {
    setActiveView(initialView);
  }, [initialView]);

  const [cmcPrice, setCmcPrice] = useState<number | null>(null);
  // const [yellowCardChannels, setYellowCardChannels] = useState<any[]>([]);

  const navigate = useNavigate();
  const username = getUser();

  // --- Data Fetching ---
  const fetchPairs = async () => {
    try {
        const res = await fetch('/api/pairs');
        const data = await res.json();
        if (Array.isArray(data)) {
            setAvailablePairs(data);
        }
    } catch (e) { console.error("Pairs Fetch Error", e); }
  };

  /*
  const fetchYellowCardChannels = async () => {
    try {
        const res = await fetch('/api/yellowcard/channels');
        const data = await res.json();
        if (Array.isArray(data)) {
            setYellowCardChannels(data);
        }
    } catch (e) { console.error("YC Channels Error", e); }
  };
  */

  const fetchCmcPrice = async () => {
    try {
        const res = await fetch(`/api/cmc/price?symbol=${selectedPair.split('/')[0]}&convert=USD`);
        const data = await res.json();
        const symbolKey = selectedPair.split('/')[0];
        if (data.data && data.data[symbolKey]) {
            setCmcPrice(data.data[symbolKey].quote.USD.price);
        }
    } catch (e) { console.error("CMC Fetch Error", e); }
  };
  const fetchMarketData = async () => {
    try {
        const res = await fetch(`/api/candles?symbol=${selectedPair}&timeframe=${timeframe}&limit=100`);
        const data = await res.json();
        setCandles(Array.isArray(data) ? data : []);
    } catch (e) { console.error(e); }
  };

  const fetchOrderBook = async () => {
    try {
        const res = await fetch(`/api/orderbook?symbol=${selectedPair}`);
        const data = await res.json();
        if (data && data.bids && data.asks) setOrderBook(data);
        else setOrderBook(null);
    } catch (e) { console.error(e); }
  };

  const fetchUserData = async () => {
      try {
          // Fetch Balance
          const bRes = await fetch(`/api/balance?username=${username}&mode=${mode}`);
          const bData = await bRes.json();
          setBalances(normalizeBalances(bData));
          
          // Fetch Orders (Mock/Real)
          const oRes = await fetch(`/api/orders?username=${username}&mode=${mode}`);
          const oData = await oRes.json();
          setMyOrders(oData.orders || []);
      } catch(e) { console.error(e); }
  };

  useEffect(() => {
    fetchPairs();
    fetchMarketData();
    fetchOrderBook();
    fetchUserData();
    fetchCmcPrice();
    // fetchYellowCardChannels();
    
    const interval = setInterval(() => {
        fetchMarketData();
        fetchOrderBook();
        fetchUserData();
        fetchCmcPrice();
    }, 10000); // Poll CMC every 10s

    return () => clearInterval(interval);
  }, [selectedPair, timeframe, mode]);

  // --- Handlers ---
  
  const handlePlaceOrder = async (order: any) => {
      try {
          const res = await fetch('/api/trade', {
              method: 'POST',
              headers: {'Content-Type': 'application/json'},
              body: JSON.stringify({
                  username,
                  symbol: selectedPair,
                  side: order.side,
                  amount: order.amount,
                  type: 'market',
                  stop_loss: order.stopLoss,
                  take_profit: order.takeProfit,
                  leverage: order.leverage,
                  mode // 'live' or 'demo'
              })
          });
          const data = await res.json();
          if (data.status === 'success') {
              showToast('Order Placed Successfully!', 'success');
              fetchUserData();
          } else {
              showToast('Order Failed: ' + data.error, 'error');
          }
      } catch (e) {
          showToast('Error placing order', 'error');
      }
  };

  const handleDeposit = () => {
      navigate('/wallet');
  };

  const handleSwap = () => {
      navigate('/defi');
  };

  // --- Render ---

  return (
    <ErrorBoundary>
      <div className={`flex h-screen font-sans overflow-hidden ${theme === 'dark' ? 'bg-gray-900 text-gray-100' : 'bg-gray-100 text-gray-900'}`}>
        
        {/* Sidebar */}
        <div className={`w-16 md:w-64 border-r flex flex-col flex-shrink-0 transition-colors duration-300 ${theme === 'dark' ? 'bg-gray-950 border-gray-800' : 'bg-white border-gray-200'}`}>
            <div className={`p-4 flex items-center gap-3 border-b ${theme === 'dark' ? 'border-gray-800' : 'border-gray-200'}`}>
                <div className="w-8 h-8 bg-indigo-600 rounded flex items-center justify-center font-bold text-white">C</div>
                <span className="font-bold text-xl hidden md:block text-indigo-400">CapaRox</span>
            </div>
            
            <nav className="flex-1 p-2 space-y-1">
                {[
                    { id: 'dashboard', icon: BarChart2, label: 'Trade' },
                    { id: 'analytics', icon: Activity, label: 'Analytics' },
                    { id: 'auto_trade', icon: Zap, label: 'Auto Bot' },
                    { id: 'coinbase', icon: Zap, label: 'Coinbase' },
                    { id: 'defi', icon: Layers, label: 'DeFi Swap' },
                    { id: 'copy_trade', icon: History, label: 'Copy Trade' },
                    { id: 'wallet', icon: Wallet, label: 'Wallet' },
                    { id: 'profile', icon: Settings, label: 'Profile' },
                ].map(item => (
                    <button 
                        key={item.id}
                        onClick={() => {
                            const route = item.id === 'dashboard' ? '/dashboard' 
                                : item.id === 'auto_trade' ? '/auto-trade'
                                : item.id === 'copy_trade' ? '/copy-trade'
                                : '/' + item.id;
                            navigate(route);
                        }}
                        className={`w-full flex items-center gap-3 px-3 py-3 rounded-lg transition-colors ${
                            activeView === item.id ? 'bg-indigo-900/50 text-indigo-400' : 'text-gray-400 hover:bg-gray-800 hover:text-white'
                        }`}
                    >
                        <item.icon size={20} />
                        <span className="hidden md:block font-medium">{item.label}</span>
                    </button>
                ))}
            </nav>

            <div className="p-4 border-t border-gray-800">
                <button onClick={() => { localStorage.removeItem('user'); navigate('/'); }} className="flex items-center gap-3 text-red-400 hover:text-red-300 transition-colors w-full px-3 py-2 rounded-lg hover:bg-red-900/20">
                    <LogOut size={20} />
                    <span className="hidden md:block font-medium">Logout</span>
                </button>
            </div>
        </div>

        {/* Main Content */}
        <div className="flex-1 flex flex-col min-w-0">
            
            {/* Top Bar */}
            <header className={`h-16 border-b flex items-center justify-between px-2 md:px-6 ${theme === 'dark' ? 'bg-gray-950 border-gray-800' : 'bg-white border-gray-200'}`}>
                <div className="flex items-center gap-2 md:gap-8 overflow-hidden">
                    {/* Pair Selector */}
                    <div className="relative group shrink-0">
                        <select 
                            value={selectedPair}
                            onChange={(e) => setSelectedPair(e.target.value)}
                            className={`flex items-center gap-2 font-bold px-3 py-1.5 rounded transition outline-none appearance-none cursor-pointer pr-8 ${theme === 'dark' ? 'bg-gray-900 text-white hover:bg-gray-800' : 'bg-gray-100 text-gray-900 hover:bg-gray-200'}`}
                        >
                            {availablePairs.length > 0 ? availablePairs.map(p => (
                                <option key={p} value={p}>{p}</option>
                            )) : (
                                <option value="BTC/USDT">BTC/USDT</option>
                            )}
                        </select>
                        <ArrowDown size={14} className="text-gray-500 absolute right-3 top-1/2 transform -translate-y-1/2 pointer-events-none" />
                    </div>

                    {/* Timeframe Selector */}
                    <div className={`flex rounded-lg p-1 gap-1 overflow-x-auto max-w-[150px] md:max-w-none no-scrollbar ${theme === 'dark' ? 'bg-gray-900' : 'bg-gray-100'}`}>
                        {['1m', '5m', '15m', '1h', '4h', '1d'].map(tf => (
                            <button 
                                key={tf}
                                onClick={() => setTimeframe(tf)}
                                className={`px-2.5 py-1 rounded text-xs font-medium transition whitespace-nowrap ${
                                    timeframe === tf 
                                    ? (theme === 'dark' ? 'bg-gray-700 text-white' : 'bg-white text-gray-900 shadow') 
                                    : 'text-gray-500 hover:text-gray-400'
                                }`}
                            >
                                {tf}
                            </button>
                        ))}
                    </div>

                    {/* Chart Type Selector */}
                    <div className={`hidden md:flex rounded-lg p-1 gap-1 border ml-2 ${theme === 'dark' ? 'bg-gray-900 border-gray-800' : 'bg-gray-100 border-gray-200'}`}>
                        <button 
                            onClick={() => setChartType('candle')}
                            className={`p-1.5 rounded transition ${chartType === 'candle' ? (theme === 'dark' ? 'bg-gray-700 text-white' : 'bg-white text-gray-900 shadow') : 'text-gray-500'}`}
                            title="Candles"
                        >
                            <BarChart2 size={16} />
                        </button>
                        <button 
                            onClick={() => setChartType('area')}
                            className={`p-1.5 rounded transition ${chartType === 'area' ? (theme === 'dark' ? 'bg-gray-700 text-white' : 'bg-white text-gray-900 shadow') : 'text-gray-500'}`}
                            title="Area"
                        >
                            <Activity size={16} />
                        </button>
                    </div>
                </div>

                <div className="flex items-center gap-4">
                    {/* Balances */}
                    <div className={`hidden md:flex items-center gap-4 text-sm px-4 py-1.5 rounded-full border ${theme === 'dark' ? 'bg-gray-900 border-gray-800' : 'bg-gray-100 border-gray-200'}`}>
                         <div className="text-gray-400">
                            CMC: <span className="text-yellow-400 font-mono">{cmcPrice ? formatMoney(cmcPrice) : '...'}</span>
                         </div>
                         <div className={`w-px h-4 ${theme === 'dark' ? 'bg-gray-700' : 'bg-gray-300'}`}></div>
                         <div className="text-gray-400">
                            Live: <span className={`${theme === 'dark' ? 'text-white' : 'text-gray-900'} font-mono`}>{formatMoney(balances?.USDT || 0)}</span>
                         </div>
                         <div className={`w-px h-4 ${theme === 'dark' ? 'bg-gray-700' : 'bg-gray-300'}`}></div>
                         <div className="text-gray-400">
                            NGN: <span className={`${theme === 'dark' ? 'text-white' : 'text-gray-900'} font-mono`}>₦{balances?.NGN?.toLocaleString() || 0}</span>
                         </div>
                    </div>

                    {/* Theme Toggle */}
                    <button 
                        onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
                        className={`p-2 rounded-lg transition-colors ${theme === 'dark' ? 'bg-gray-900 text-yellow-400 hover:bg-gray-800' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'}`}
                        title={theme === 'dark' ? "Switch to Light Mode" : "Switch to Dark Mode"}
                    >
                        {theme === 'dark' ? <Sun size={18} /> : <Moon size={18} />}
                    </button>

                    {/* Mode Toggle */}
                    <div className={`flex p-1 rounded-lg border ${theme === 'dark' ? 'bg-gray-900 border-gray-700' : 'bg-gray-100 border-gray-200'}`}>
                        <button 
                            onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
                            className={`px-3 py-1 rounded text-xs font-bold transition ${theme === 'light' ? 'bg-gray-200 text-gray-800' : 'text-gray-500 hover:text-gray-300'}`}
                        >
                            {theme === 'dark' ? '☀' : '☾'}
                        </button>
                        <div className="w-px bg-gray-700 mx-1"></div>
                        <button 
                            onClick={() => setMode('demo')}
                            className={`px-3 py-1 rounded text-xs font-bold transition ${mode === 'demo' ? 'bg-indigo-600 text-white shadow' : 'text-gray-500'}`}
                        >
                            DEMO
                        </button>
                        <button 
                            onClick={() => setMode('live')}
                            className={`px-3 py-1 rounded text-xs font-bold transition ${mode === 'live' ? 'bg-red-600 text-white shadow' : 'text-gray-500'}`}
                        >
                            LIVE
                        </button>
                    </div>

                    <div className="flex items-center gap-3 pl-4 border-l border-gray-700/50">
                        <div className="text-right hidden sm:block">
                            <div className={`text-sm font-bold ${theme === 'dark' ? 'text-white' : 'text-gray-900'}`}>{username}</div>
                            <div className="text-xs text-gray-500">Pro Trader</div>
                        </div>
                        <button className="w-8 h-8 rounded-full bg-indigo-600 flex items-center justify-center text-white font-bold shadow-lg ring-2 ring-indigo-500/20">
                            {username[0].toUpperCase()}
                        </button>
                    </div>
                </div>
            </header>

            {/* Content Area */}
            <main className="flex-1 overflow-hidden relative">
                {activeView === 'dashboard' && (
                    <div className="flex flex-col lg:flex-row h-full overflow-y-auto lg:overflow-hidden">
                        {/* Left: Chart & Bottom Panel */}
                        <div className="flex-1 flex flex-col min-h-[500px] lg:min-h-0">
                            {/* Chart Area */}
                            <div className="flex-1 bg-gray-900 relative border-b border-gray-800 min-h-[300px]">
                                <ChartPanel candles={candles} theme="dark" chartType={chartType} />
                                {/* Overlay Stats */}
                                <div className="absolute top-4 left-4 z-10 flex gap-2">
                                    <SignalCard symbol={selectedPair.replace('/', '')} />
                                </div>
                            </div>
                            
                            {/* Bottom Panel (Positions) */}
                            <div className="h-64 bg-gray-950 border-t border-gray-800 flex flex-col">
                                <div className="flex border-b border-gray-800">
                                    <button className="px-4 py-2 text-sm font-medium text-indigo-400 border-b-2 border-indigo-400 bg-gray-900">Open Positions</button>
                                    <button className="px-4 py-2 text-sm font-medium text-gray-500 hover:text-gray-300">Order History</button>
                                </div>
                                <div className="flex-1 overflow-x-auto p-0">
                                    <table className="w-full text-left text-sm text-gray-400 min-w-[600px]">
                                        <thead className="bg-gray-900 text-xs uppercase font-medium text-gray-500 sticky top-0">
                                            <tr>
                                                <th className="px-4 py-2">Symbol</th>
                                                <th className="px-4 py-2">Side</th>
                                                <th className="px-4 py-2">Size</th>
                                                <th className="px-4 py-2">Entry Price</th>
                                                <th className="px-4 py-2">Mark Price</th>
                                                <th className="px-4 py-2">PNL</th>
                                                <th className="px-4 py-2">Action</th>
                                            </tr>
                                        </thead>
                                        <tbody className="divide-y divide-gray-800">
                                            {myOrders.length > 0 ? myOrders.map(order => (
                                                <tr key={order.id} className="hover:bg-gray-900/50">
                                                    <td className="px-4 py-2 font-bold text-white">{order.symbol}</td>
                                                    <td className={`px-4 py-2 ${order.side === 'buy' ? 'text-green-400' : 'text-red-400'}`}>{order.side.toUpperCase()}</td>
                                                    <td className="px-4 py-2">{order.amount}</td>
                                                    <td className="px-4 py-2">{order.price}</td>
                                                    <td className="px-4 py-2">{candles[candles.length-1]?.close || '-'}</td>
                                                    <td className="px-4 py-2 text-green-400">+0.00</td>
                                                    <td className="px-4 py-2">
                                                        <button className="text-xs bg-red-900/30 text-red-400 px-2 py-1 rounded hover:bg-red-900/50 border border-red-900">Close</button>
                                                    </td>
                                                </tr>
                                            )) : (
                                                <tr>
                                                    <td colSpan={7} className="px-4 py-8 text-center text-gray-600">No open positions</td>
                                                </tr>
                                            )}
                                        </tbody>
                                    </table>
                                </div>
                            </div>
                        </div>

                        {/* Right: Order Entry & Book */}
                        <div className="w-full lg:w-72 bg-gray-950 border-t lg:border-t-0 lg:border-l border-gray-800 flex flex-col h-auto lg:h-full">
                            {/* Order Book */}
                            <div className="h-64 lg:h-1/2 border-b border-gray-800 p-2">
                                <h3 className="text-xs font-bold text-gray-500 mb-2 uppercase">Order Book</h3>
                                <OrderBook data={orderBook} />
                            </div>

                            {/* Order Entry */}
                            <div className="flex-1 flex flex-col min-h-0">
                                <TradePanel 
                                    symbol={selectedPair}
                                    candles={candles}
                                    balance={Number(balances?.USDT || 0)}
                                    onPlaceOrder={handlePlaceOrder}
                                    onDeposit={handleDeposit}
                                    onSwap={handleSwap}
                                />
                            </div>
                        </div>
                    </div>
                )}

                {activeView === 'analytics' && <AdvancedAnalytics symbol={selectedPair} />}

                {activeView === 'auto_trade' && (
                    <div className="h-full overflow-y-auto custom-scrollbar">
                        <AutoTradingPanel />
                    </div>
                )}

                {activeView === 'coinbase' && (
                    <div className="p-6 h-full overflow-y-auto">
                        <h2 className="text-2xl font-bold text-white mb-6 flex items-center gap-2">
                            <Zap className="text-blue-400" /> Coinbase Advanced Integration
                        </h2>
                        <CoinbasePanel />
                    </div>
                )}
                
                {/* Placeholder for DeFi */}
                {activeView === 'defi' && <DeFiModule balances={balances} onSuccess={fetchUserData} />}

                {/* Copy Trading */}
                {activeView === 'copy_trade' && <CopyTradingModule />}

                {/* Profile View */}
                {activeView === 'profile' && (
                    <div className="p-4 md:p-6 h-full overflow-y-auto custom-scrollbar">
                        <Profile username={username} />
                    </div>
                )}
                
                {/* Wallet Module */}
                {activeView === 'wallet' && <FundsManager balances={balances} onRefresh={fetchUserData} />}
                
            </main>
        </div>
      </div>
    </ErrorBoundary>
  );
}
