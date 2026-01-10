import { useEffect, useRef, useState } from "react"; 
import { createChart, IChartApi, ColorType } from "lightweight-charts"; 

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

const TopBar = () => ( 
  <div className="flex justify-between items-center bg-white shadow px-4 py-2"> 
    <div className="font-bold text-xl text-indigo-600">CapaRox Bot</div>
    <div className="flex gap-4 items-center"> 
      <div className="text-sm text-green-600 bg-green-100 px-2 py-1 rounded">● Online</div>
      <button>🔔</button> 
      <div className="w-8 h-8 bg-gray-300 rounded-full" /> 
    </div> 
  </div> 
); 

const Sidebar = () => ( 
  <div className="w-60 bg-gray-900 text-white h-screen p-4 flex flex-col gap-6"> 
    <div className="text-2xl font-bold mb-4">Menu</div>
    <nav className="flex flex-col gap-4"> 
      <a href="/" className="hover:text-indigo-400">📊 Dashboard</a> 
      <a href="#" className="hover:text-indigo-400">📈 Markets</a> 
      <a href="#" className="hover:text-indigo-400">💳 Wallet</a> 
      <a href="#" className="hover:text-indigo-400">⚙️ Settings</a> 
    </nav> 
  </div> 
); 

const ChartPanel = ({ candles }: { candles: Candle[] }) => { 
  const ref = useRef<HTMLDivElement>(null); 
  const chartRef = useRef<IChartApi | null>(null);

  useEffect(() => { 
    if (!ref.current) return; 
    
    // Cleanup previous chart
    if (chartRef.current) {
        chartRef.current.remove();
    }

    const chart = createChart(ref.current, { 
      width: ref.current.clientWidth, 
      height: 400, 
      layout: { background: { type: ColorType.Solid, color: "#ffffff" }, textColor: "#333" }, 
      grid: { vertLines: { color: "#f0f0f0" }, horzLines: { color: "#f0f0f0" } },
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
  <div className="bg-white p-4 shadow rounded h-[200px] overflow-auto"> 
    <h3 className="font-semibold mb-2 text-gray-700">Order Book (BTC/USDT)</h3> 
    <div className="flex justify-between text-xs text-gray-500 mb-1"> 
      <span>Price</span> 
      <span>Amount</span> 
    </div> 
    {data ? (
        <>
            {data.asks.slice(0, 5).reverse().map((ask, i) => (
                <div key={`ask-${i}`} className="flex justify-between text-xs">
                    <span className="text-red-500">{ask.price.toFixed(2)}</span>
                    <span className="text-gray-600">{ask.amount.toFixed(4)}</span>
                </div>
            ))}
            <div className="h-px bg-gray-200 my-1"></div>
            {data.bids.slice(0, 5).map((bid, i) => (
                <div key={`bid-${i}`} className="flex justify-between text-xs">
                    <span className="text-green-500">{bid.price.toFixed(2)}</span>
                    <span className="text-gray-600">{bid.amount.toFixed(4)}</span>
                </div>
            ))}
        </>
    ) : (
        <div className="text-sm text-gray-400">Loading...</div>
    )}
  </div> 
); 

const TradeHistory = ({ trades }: { trades: Trade[] }) => ( 
  <div className="bg-white p-4 shadow rounded mt-4 h-[200px] overflow-auto"> 
    <h3 className="font-semibold mb-2 text-gray-700">Recent Trades</h3> 
    {trades.length > 0 ? (
        trades.map((t, i) => (
            <div key={i} className="flex justify-between text-xs py-1 border-b border-gray-100 last:border-0">
                <span className={t.side === 'buy' ? 'text-green-600' : 'text-red-600'}>
                    {t.side.toUpperCase()} {t.amount}
                </span>
                <span className="text-gray-500">@ {t.price}</span>
            </div>
        ))
    ) : (
        <div className="text-sm text-gray-400">No trades yet</div>
    )}
  </div> 
); 

const TradingPanel = () => ( 
  <div className="bg-white p-4 shadow rounded mt-4 flex gap-4"> 
    <form className="flex-1" onSubmit={(e) => e.preventDefault()}> 
      <h3 className="text-green-600 font-semibold mb-2">Buy BTC</h3> 
      <input 
        type="number" 
        placeholder="Price (USDT)" 
        className="border rounded px-3 py-2 w-full mb-3 text-sm" 
      /> 
      <input 
        type="number" 
        placeholder="Amount (BTC)" 
        className="border rounded px-3 py-2 w-full mb-3 text-sm" 
      /> 
      <button className="bg-green-500 hover:bg-green-600 text-white font-medium px-4 py-2 rounded w-full transition"> 
        Buy BTC
      </button> 
    </form> 
    <div className="w-px bg-gray-200"></div>
    <form className="flex-1" onSubmit={(e) => e.preventDefault()}> 
      <h3 className="text-red-600 font-semibold mb-2">Sell BTC</h3> 
      <input 
        type="number" 
        placeholder="Price (USDT)" 
        className="border rounded px-3 py-2 w-full mb-3 text-sm" 
      /> 
      <input 
        type="number" 
        placeholder="Amount (BTC)" 
        className="border rounded px-3 py-2 w-full mb-3 text-sm" 
      /> 
      <button className="bg-red-500 hover:bg-red-600 text-white font-medium px-4 py-2 rounded w-full transition"> 
        Sell BTC 
      </button> 
    </form> 
  </div> 
); 

export const Dashboard = () => {
    const [candles, setCandles] = useState<Candle[]>([]);
    const [orderBook, setOrderBook] = useState<OrderBookData | null>(null);
    const [trades, setTrades] = useState<Trade[]>([]);

    useEffect(() => {
        const fetchData = async () => {
            try {
                // Fetch Candles
                const cRes = await fetch('/api/candles?symbol=BTCUSDT&limit=100');
                const cData = await cRes.json();
                if (Array.isArray(cData)) setCandles(cData);

                // Fetch Orderbook
                const obRes = await fetch('/api/orderbook?symbol=BTCUSDT');
                const obData = await obRes.json();
                setOrderBook(obData);

                // Fetch Trades
                const tRes = await fetch('/api/trades');
                const tData = await tRes.json();
                if (Array.isArray(tData)) setTrades(tData);

            } catch (e) {
                console.error("Failed to fetch data:", e);
            }
        };

        fetchData();
        const interval = setInterval(fetchData, 3000); // Poll every 3s
        return () => clearInterval(interval);
    }, []);

    return ( 
    <div className="flex bg-gray-50 min-h-screen"> 
        <Sidebar /> 
        <div className="flex-1 flex flex-col"> 
        <TopBar /> 
        <div className="p-6 grid grid-cols-1 lg:grid-cols-3 gap-6 flex-1 overflow-auto"> 
            <div className="lg:col-span-2 flex flex-col gap-6"> 
            <div className="bg-white p-4 rounded shadow">
                <h2 className="font-bold text-lg mb-2 text-gray-700">BTC/USDT Chart</h2>
                <ChartPanel candles={candles} /> 
            </div>
            <TradingPanel /> 
            </div> 
            <div className="flex flex-col gap-6"> 
            <OrderBook data={orderBook} /> 
            <TradeHistory trades={trades} /> 
            <div className="bg-indigo-600 text-white p-4 rounded shadow mt-auto">
                <h3 className="font-bold mb-1">Status</h3>
                <p className="text-sm opacity-90">Bot is currently active and scanning markets.</p>
            </div>
            </div> 
        </div> 
        </div> 
    </div> 
    );
};
