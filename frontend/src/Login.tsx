import React, { useState, useEffect } from 'react';
import { useNavigate, Link, useLocation } from 'react-router-dom';
import { FcGoogle } from 'react-icons/fc';
import { FaGithub } from 'react-icons/fa';

export const Login = () => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [providers, setProviders] = useState({ google: false, github: false });
  const navigate = useNavigate();
  const location = useLocation();

  useEffect(() => {
    // Check available auth providers
    fetch('/api/auth/providers')
      .then(res => res.json())
      .then(data => setProviders(data))
      .catch(err => console.error('Failed to fetch auth providers', err));

    if (location.state && location.state.message) {
      setSuccess(location.state.message);
      // Clear state so refresh doesn't show it again
      window.history.replaceState({}, document.title);
    }
    
    // Check for error in URL params (e.g. from OAuth redirect)
    const params = new URLSearchParams(location.search);
    const errorMsg = params.get('error');
    if (errorMsg) {
      setError(errorMsg);
      // Clean up the URL
      window.history.replaceState({}, document.title, window.location.pathname);
    }

    // Check for auth_check flag (from OAuth success)
    if (params.get('auth_check')) {
      fetch('/api/auth/me')
        .then(res => {
          if (res.ok) return res.json();
          throw new Error('Auth check failed');
        })
        .then(data => {
          localStorage.setItem('user', JSON.stringify(data));
          navigate('/dashboard');
        })
        .catch(err => {
          console.error(err);
          // Optional: setError('Login verification failed');
        });
    }
  }, [location]);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const res = await fetch('/api/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password })
      });
      const data = await res.json();
      if (res.ok) {
        localStorage.setItem('user', JSON.stringify(data));
        navigate('/dashboard');
      } else {
        setError(data.error || 'Login failed');
      }
    } catch (err) {
      setError('Network error');
    }
  };

  return (
    <div className="flex items-center justify-center min-h-screen bg-gray-900 px-4 py-12">
      <div className="bg-gray-800 p-8 rounded-lg shadow-lg w-full max-w-md">
        <h2 className="text-3xl font-bold text-white mb-6 text-center">Login</h2>
        {success && <div className="bg-green-500 text-white p-2 rounded mb-4 text-sm text-center">{success}</div>}
        {error && <div className="bg-red-500 text-white p-2 rounded mb-4 text-sm text-center">{error}</div>}
        <form onSubmit={handleLogin}>
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
          <button type="submit" className="w-full bg-indigo-600 hover:bg-indigo-700 text-white font-bold py-2 px-4 rounded transition">
            Login
          </button>
        </form>

        {(providers.google || providers.github) && (
          <>
            <div className="mt-6 flex items-center justify-between">
              <span className="border-b border-gray-600 w-1/5 lg:w-1/4"></span>
              <span className="text-xs text-center text-gray-500 uppercase">or login with</span>
              <span className="border-b border-gray-600 w-1/5 lg:w-1/4"></span>
            </div>

            <div className="mt-6 flex gap-4">
              {providers.google && (
                <button
                  type="button"
                  onClick={() => window.location.href = '/api/auth/login/google'}
                  className="w-full flex justify-center items-center gap-2 bg-white text-gray-700 font-bold py-2 px-4 rounded hover:bg-gray-100 transition"
                >
                  <FcGoogle size={20} /> Google
                </button>
              )}
              {providers.github && (
                <button
                  type="button"
                  onClick={() => window.location.href = '/api/auth/login/github'}
                  className="w-full flex justify-center items-center gap-2 bg-gray-700 text-white font-bold py-2 px-4 rounded hover:bg-gray-600 transition border border-gray-600"
                >
                  <FaGithub size={20} /> GitHub
                </button>
              )}
            </div>
          </>
        )}

        <div className="mt-4 text-center">
          <Link to="/register" className="text-indigo-400 hover:text-indigo-300 text-sm">Create an account</Link>
        </div>
      </div>
    </div>
  );
};
