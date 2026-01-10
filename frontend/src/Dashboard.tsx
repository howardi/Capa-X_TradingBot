import { useEffect, useRef, useState } from "react"; 
import { createChart, IChartApi, ColorType } from "lightweight-charts"; 
import { useNavigate } from "react-router-dom";

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

interface Trade {
  symbol: string;
  side: string;
  amount: number;
  price: number;
  timestamp: number;
}

interface Balances {
    USDT: number;
    NGN: number;
    BTC: number;
    ETH: number;
}

interface AutoTradeLog {
    time: string;
    message: string;
    type: 'info' | 'success' | 'warning' | 'error';
}

const TopBar = ({ balances }: { balances: Balances | null }) => ( 
  <div className="flex justify-between items-center bg-white shadow px-4 py-2 sticky top-0 z-10"> 
    <div className="font-bold text-xl text-indigo-600">CapaRox Bot</div>
    <div className="flex gap-4 items-center"> 
      <div className="hidden md:flex gap-4 mr-4 text-sm font-medium">
         <div className="text-gray-600">
            USDT: <span className="text-gray-900">{balances?.USDT.toFixed(2) || '...'}</span>
         </div>
         <div className="text-gray-600">
            NGN: <span className="text-gray-900">₦{balances?.NGN.toLocaleString() || '...'}</span>
         </div>
      </div>
      <div className="text-sm text-green-600 bg-green-100 px-2 py-1 rounded flex items-center gap-1">
        <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></span> Online
      </div>
      <button>🔔</button> 
      <div className="w-8 h-8 bg-gray-300 rounded-full" /> 
    </div> 
  </div> 
); 

const Sidebar = () => {
  const navigate = useNavigate();
  const handleLogout = () => {
    localStorage.removeItem('user');
    navigate('/');
  };

  return (
    <div className="w-60 bg-gray-900 text-white h-screen p-4 flex flex-col gap-6 fixed left-0 top-0 overflow-y-auto"> 
      <div className="text-2xl font-bold mb-4 px-2">Menu</div>
      <nav className="flex flex-col gap-2"> 
        <a href="#" className="hover:bg-gray-800 px-4 py-2 rounded text-indigo-400 font-medium">📊 Dashboard</a> 
        <a href="#" className="hover:bg-gray-800 px-4 py-2 rounded text-gray-400">📈 Markets</a> 
        <a href="#" className="hover:bg-gray-800 px-4 py-2 rounded text-gray-400">💳 Wallet</a> 
        <a href="#" className="hover:bg-gray-800 px-4 py-2 rounded text-gray-400">⚙️ Settings</a> 
      </nav> 
      <div className="mt-auto">
        <button onClick={handleLogout} className="w-full text-left hover:bg-gray-800 px-4 py-2 rounded text-red-400">
          🚪 Logout
        </button>
      </div>
    </div> 
  );
};

const ChartPanel = ({ candles }: { candles: Candle[] }) => { 
  const ref = useRef<HTMLDivElement>(null); 
  const chartRef = useRef<IChartApi | null>(null);

  useEffect(() => { 
    if (!ref.current) return; 
    
    if (chartRef.current) {
        chartRef.current.remove();
    }

    const chart = createChart(ref.current, { 
      width: ref.current.clientWidth, 
      height: 400, 
      layout: { background: { type: ColorType.Solid, color: "#ffffff" }, textColor: "#333" }, 
      grid: { vertLines: { color: "#f0f0f0" }, horzLines: { color: "#f0f0f0" } },
      timeScale: { timeVisible: true, secondsVisible: false }
    }); 
    
    chartRef.current = chart;

    const series = chart.addCandlestickSeries({
        upColor: '#26a69a', downColor: '#ef5350', borderVisible: false, wickUpColor: '#26a69a', wickDownColor: '#ef5350',
    }); 
    
    if (candles.length > 0) {
        series.setData(candles as any); 
    }

    const handleResize = () => {
        if (ref.current) {
            chart.applyOptions({ width: ref.current.clientWidth });
        }
    };

    window.addEventListener('resize', handleResize);

    return () => {
        window.removeEventListener('resize', handleResize);
        chart.remove(); 
    }
  }, [candles]); 

  return <div ref={ref} className="w-full h-[400px]" />; 
}; 

const OrderBook = ({ data }: { data: OrderBookData | null }) => ( 
  <div className="bg-white p-4 shadow rounded h-[300px] overflow-hidden flex flex-col"> 
    <h3 className="font-semibold mb-2 text-gray-700">Order Book (BTC/USDT)</h3> 
    <div className="flex justify-between text-xs text-gray-500 mb-1 font-medium"> 
      <span>Price</span> 
      <span>Amount</span> 
    </div> 
    <div className="flex-1 overflow-auto">
    {data ? (
        <>
            {data.asks.slice(0, 8).reverse().map((ask, i) => (
                <div key={`ask-${i}`} className="flex justify-between text-xs py-0.5">
                    <span className="text-red-500 font-mono">{ask.price.toFixed(2)}</span>
                    <span className="text-gray-600 font-mono">{ask.amount.toFixed(4)}</span>
                </div>
            ))}
            <div className="h-px bg-gray-200 my-2"></div>
            {data.bids.slice(0, 8).map((bid, i) => (
                <div key={`bid-${i}`} className="flex justify-between text-xs py-0.5">
                    <span className="text-green-500 font-mono">{bid.price.toFixed(2)}</span>
                    <span className="text-gray-600 font-mono">{bid.amount.toFixed(4)}</span>
                </div>
            ))}
        </>
    ) : (
        <div className="flex items-center justify-center h-full text-sm text-gray-400">Loading...</div>
    )}
    </div>
  </div> 
); 

const TradeHistory = ({ trades }: { trades: Trade[] }) => ( 
  <div className="bg-white p-4 shadow rounded h-[300px] overflow-hidden flex flex-col"> 
    <h3 className="font-semibold mb-2 text-gray-700">Recent Trades</h3> 
    <div className="flex-1 overflow-auto">
    {trades.length > 0 ? (
        trades.map((t, i) => (
            <div key={i} className="flex justify-between text-xs py-1 border-b border-gray-100 last:border-0">
                <span className={t.side === 'buy' ? 'text-green-600' : 'text-red-600'}>
                    {t.side.toUpperCase()} {t.amount}
                </span>
                <span className="text-gray-500 font-mono">{t.price}</span>
            </div>
        ))
    ) : (
        <div className="flex items-center justify-center h-full text-sm text-gray-400">No trades yet</div>
    )}
    </div>
  </div> 
); 

const TradingPanel = ({ onTrade }: { onTrade: (side: string, price: number, amount: number) => void }) => {
    const [buyPrice, setBuyPrice] = useState('');
    const [buyAmount, setBuyAmount] = useState('');
    const [sellPrice, setSellPrice] = useState('');
    const [sellAmount, setSellAmount] = useState('');

    const handleBuy = (e: React.FormEvent) => {
        e.preventDefault();
        onTrade('buy', parseFloat(buyPrice), parseFloat(buyAmount));
    };

    const handleSell = (e: React.FormEvent) => {
        e.preventDefault();
        onTrade('sell', parseFloat(sellPrice), parseFloat(sellAmount));
    };

    return ( 
      <div className="bg-white p-4 shadow rounded flex gap-4"> 
        <form className="flex-1" onSubmit={handleBuy}> 
          <h3 className="text-green-600 font-semibold mb-2">Buy BTC</h3> 
          <input 
            type="number" 
            placeholder="Price (USDT)" 
            className="border rounded px-3 py-2 w-full mb-3 text-sm focus:outline-none focus:ring-2 focus:ring-green-500" 
            value={buyPrice}
            onChange={e => setBuyPrice(e.target.value)}
          /> 
          <input 
            type="number" 
            placeholder="Amount (BTC)" 
            className="border rounded px-3 py-2 w-full mb-3 text-sm focus:outline-none focus:ring-2 focus:ring-green-500" 
            value={buyAmount}
            onChange={e => setBuyAmount(e.target.value)}
          /> 
          <button type="submit" className="bg-green-500 hover:bg-green-600 text-white font-medium px-4 py-2 rounded w-full transition"> 
            Buy BTC
          </button> 
        </form> 
        <div className="w-px bg-gray-200"></div>
        <form className="flex-1" onSubmit={handleSell}> 
          <h3 className="text-red-600 font-semibold mb-2">Sell BTC</h3> 
          <input 
            type="number" 
            placeholder="Price (USDT)" 
            className="border rounded px-3 py-2 w-full mb-3 text-sm focus:outline-none focus:ring-2 focus:ring-red-500" 
            value={sellPrice}
            onChange={e => setSellPrice(e.target.value)}
          /> 
          <input 
            type="number" 
            placeholder="Amount (BTC)" 
            className="border rounded px-3 py-2 w-full mb-3 text-sm focus:outline-none focus:ring-2 focus:ring-red-500" 
            value={sellAmount}
            onChange={e => setSellAmount(e.target.value)}
          /> 
          <button type="submit" className="bg-red-500 hover:bg-red-600 text-white font-medium px-4 py-2 rounded w-full transition"> 
            Sell BTC 
          </button> 
        </form> 
      </div> 
    ); 
};

export const Dashboard = () => {
    const [candles, setCandles] = useState<Candle[]>([]);
    const [orderBook, setOrderBook] = useState<OrderBookData | null>(null);
    const [trades, setTrades] = useState<Trade[]>([]);
    const [balances, setBalances] = useState<Balances | null>(null);
    const [isAutoTrading, setIsAutoTrading] = useState(false);
    const [autoLogs, setAutoLogs] = useState<AutoTradeLog[]>([]);

    const addLog = (msg: string, type: 'info' | 'success' | 'warning' | 'error' = 'info') => {
        setAutoLogs(prev => [{ time: new Date().toLocaleTimeString(), message: msg, type }, ...prev.slice(0, 9)]);
    };

    const fetchData = async () => {
        try {
            // Fetch Candles
            const cRes = await fetch('/api/candles?symbol=BTC/USDT&limit=100');
            const cData = await cRes.json();
            if (Array.isArray(cData)) setCandles(cData);

            // Fetch Orderbook
            const obRes = await fetch('/api/orderbook?symbol=BTC/USDT');
            const obData = await obRes.json();
            setOrderBook(obData);

            // Fetch Trades
            const tRes = await fetch('/api/trades?symbol=BTC/USDT');
            const tData = await tRes.json();
            if (Array.isArray(tData)) setTrades(tData);

            // Fetch Balances
            const bRes = await fetch('/api/balance');
            const bData = await bRes.json();
            setBalances(bData);

        } catch (e) {
            console.error("Failed to fetch data:", e);
        }
    };

    // Auto Trading Logic
    useEffect(() => {
        let interval: any;
        if (isAutoTrading) {
            addLog('Auto Trading Started', 'success');
            interval = setInterval(async () => {
                try {
                    addLog('Scanning market...', 'info');
                    const res = await fetch('/api/analyze?symbol=BTC/USDT');
                    const data = await res.json();
                    
                    if (data.signal === 'buy') {
                        addLog(`Signal BUY at ${data.price} (SMA: ${data.sma_10.toFixed(2)})`, 'success');
                        // Execute Buy
                        await handleTrade('buy', data.price, 0.0001); // Small amount for demo
                    } else if (data.signal === 'sell') {
                        addLog(`Signal SELL at ${data.price} (SMA: ${data.sma_10.toFixed(2)})`, 'warning');
                        // Execute Sell
                        await handleTrade('sell', data.price, 0.0001);
                    } else {
                        addLog(`Holding. Price: ${data.price} vs SMA: ${data.sma_10?.toFixed(2)}`, 'info');
                    }
                } catch (e) {
                    addLog('Auto trade error', 'error');
                }
            }, 10000); // Scan every 10s
        } else {
            if(autoLogs.length > 0 && autoLogs[0].message !== 'Auto Trading Stopped')
                addLog('Auto Trading Stopped', 'warning');
        }
        return () => clearInterval(interval);
    }, [isAutoTrading]);

    useEffect(() => {
        fetchData();
        const interval = setInterval(fetchData, 3000); // Poll every 3s
        return () => clearInterval(interval);
    }, []);

    const handleTrade = async (side: string, price: number, amount: number) => {
        try {
            if (!price || !amount) {
                alert("Please enter price and amount");
                return;
            }
            const res = await fetch('/api/trade', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ symbol: 'BTC/USDT', side, price, amount, type: 'limit' })
            });
            const data = await res.json();
            if (data.error) {
                addLog(`Trade Failed: ${data.error}`, 'error');
                if(!isAutoTrading) alert(`Error: ${data.error}`);
            } else {
                addLog(`Order Placed: ${side.toUpperCase()} ${amount} @ ${price}`, 'success');
                if(!isAutoTrading) alert(`Order Placed! ID: ${data.orderId}`);
                fetchData(); // Refresh data
            }
        } catch (e) {
            addLog(`Network Error: ${e}`, 'error');
            if(!isAutoTrading) alert(`Network Error: ${e}`);
        }
    };

    return ( 
    <div className="flex bg-gray-50 min-h-screen"> 
        <Sidebar /> 
        <div className="flex-1 flex flex-col ml-60"> 
        <TopBar balances={balances} /> 
        <div className="p-6 grid grid-cols-1 lg:grid-cols-3 gap-6 flex-1 overflow-auto"> 
            <div className="lg:col-span-2 flex flex-col gap-6"> 
                <div className="bg-white p-4 rounded shadow">
                    <h2 className="font-bold text-lg mb-2 text-gray-700">BTC/USDT Chart</h2>
                    <ChartPanel candles={candles} /> 
                </div>
                
                {/* Auto Trading Control Panel */}
                <div className="bg-white p-4 rounded shadow">
                    <div className="flex justify-between items-center mb-4">
                        <div className="flex items-center gap-2">
                            <h2 className="font-bold text-lg text-gray-700">Auto Trading Bot</h2>
                            <span className="text-xs bg-blue-100 text-blue-800 px-2 py-0.5 rounded">SMA Strategy</span>
                        </div>
                        <div className="flex items-center">
                            <label className="relative inline-flex items-center cursor-pointer">
                                <input type="checkbox" className="sr-only peer" checked={isAutoTrading} onChange={e => setIsAutoTrading(e.target.checked)} />
                                <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-indigo-600"></div>
                                <span className="ml-3 text-sm font-medium text-gray-900">{isAutoTrading ? 'Enabled' : 'Disabled'}</span>
                            </label>
                        </div>
                    </div>
                    
                    <div className="bg-gray-900 rounded p-3 h-32 overflow-auto font-mono text-xs text-gray-300">
                        {autoLogs.length === 0 && <div className="text-gray-500 italic">Logs will appear here...</div>}
                        {autoLogs.map((log, i) => (
                            <div key={i} className="mb-1">
                                <span className="text-gray-500">[{log.time}]</span>{' '}
                                <span className={
                                    log.type === 'success' ? 'text-green-400' :
                                    log.type === 'error' ? 'text-red-400' :
                                    log.type === 'warning' ? 'text-yellow-400' : 'text-blue-300'
                                }>{log.message}</span>
                            </div>
                        ))}
                    </div>
                </div>

                <TradingPanel onTrade={handleTrade} /> 
            </div> 
            <div className="flex flex-col gap-6"> 
                <OrderBook data={orderBook} /> 
                <TradeHistory trades={trades} /> 
                <div className="bg-indigo-600 text-white p-4 rounded shadow mt-auto">
                    <h3 className="font-bold mb-1">Status</h3>
                    <p className="text-sm opacity-90">Bot is {isAutoTrading ? 'RUNNING' : 'IDLE'}. Scanning BTC/USDT markets.</p>
                </div>
            </div> 
        </div> 
        </div> 
    </div> 
    );
};
