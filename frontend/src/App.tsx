import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import Dashboard from './Dashboard';
import { Login } from './Login';
import { Register } from './Register';

function App() {
  const PrivateRoute = ({ children }: { children: JSX.Element }) => {
    const user = localStorage.getItem('user');
    return user ? children : <Navigate to="/" />;
  };

  return (
    <Router>
      <Routes>
        <Route path="/" element={<Login />} />
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route path="/dashboard" element={
          <PrivateRoute>
            <Dashboard initialView="dashboard" />
          </PrivateRoute>
        } />
        <Route path="/wallet" element={
          <PrivateRoute>
            <Dashboard initialView="wallet" />
          </PrivateRoute>
        } />
        <Route path="/defi" element={
          <PrivateRoute>
            <Dashboard initialView="defi" />
          </PrivateRoute>
        } />
        <Route path="/analytics" element={
          <PrivateRoute>
            <Dashboard initialView="analytics" />
          </PrivateRoute>
        } />
        <Route path="/auto-trade" element={
          <PrivateRoute>
            <Dashboard initialView="auto_trade" />
          </PrivateRoute>
        } />
        <Route path="/copy-trade" element={
          <PrivateRoute>
            <Dashboard initialView="copy_trade" />
          </PrivateRoute>
        } />
        <Route path="/profile" element={
          <PrivateRoute>
            <Dashboard initialView="profile" />
          </PrivateRoute>
        } />
        <Route path="/coinbase" element={
          <PrivateRoute>
            <Dashboard initialView="coinbase" />
          </PrivateRoute>
        } />
      </Routes>
    </Router>
  );
}

export default App;
