import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';

export const Register = () => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const navigate = useNavigate();

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const res = await fetch('/api/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password })
      });
      const data = await res.json();
      if (res.ok) {
        alert('Registration successful! Please login.');
        navigate('/');
      } else {
        setError(data.error || 'Registration failed');
      }
    } catch (err) {
      setError('Network error');
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-900">
      <div className="bg-gray-800 p-8 rounded-lg shadow-lg w-96">
        <h2 className="text-2xl font-bold text-white mb-6 text-center">Create Account</h2>
        {error && <div className="bg-red-500 text-white p-2 rounded mb-4 text-sm">{error}</div>}
        <form onSubmit={handleRegister}>
          <div className="mb-4">
            <label className="block text-gray-300 text-sm font-bold mb-2">Username</label>
            <input 
              type="text" 
              className="w-full p-2 rounded bg-gray-700 text-white border border-gray-600 focus:border-indigo-500 outline-none"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
            />
          </div>
          <div className="mb-6">
            <label className="block text-gray-300 text-sm font-bold mb-2">Password</label>
            <input 
              type="password" 
              className="w-full p-2 rounded bg-gray-700 text-white border border-gray-600 focus:border-indigo-500 outline-none"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>
          <button type="submit" className="w-full bg-green-600 hover:bg-green-700 text-white font-bold py-2 px-4 rounded transition">
            Register
          </button>
        </form>
        <div className="mt-4 text-center">
          <Link to="/" className="text-indigo-400 hover:text-indigo-300 text-sm">Back to Login</Link>
        </div>
      </div>
    </div>
  );
};
