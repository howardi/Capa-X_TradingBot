import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { Dashboard } from './Dashboard';
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
        <Route path="/register" element={<Register />} />
        <Route path="/dashboard" element={
          <PrivateRoute>
            <Dashboard />
          </PrivateRoute>
        } />
      </Routes>
    </Router>
  );
}

export default App;
