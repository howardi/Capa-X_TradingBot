import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';

export const Register = () => {
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [phoneNumber, setPhoneNumber] = useState('');
  const [securityAnswer, setSecurityAnswer] = useState('');
  const [error, setError] = useState('');
  const navigate = useNavigate();

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const res = await fetch('/api/auth/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          username, 
          email, 
          password, 
          full_name: fullName, 
          phone_number: phoneNumber,
          security_answer: securityAnswer 
        })
      });
      const data = await res.json();
      if (res.ok) {
        // Professional UI Feedback instead of alert
        setError(''); // Clear any errors
        // Show success state briefly or redirect with state
        navigate('/', { state: { message: 'Registration successful! Please login.' } });
      } else {
        setError(data.error || 'Registration failed');
      }
    } catch (err) {
      setError('Network error: Ensure backend is running');
    }
  };

  return (
    <div className="flex items-center justify-center min-h-screen bg-gray-900 px-4 py-12">
      <div className="bg-gray-800 p-8 rounded-lg shadow-lg w-full max-w-md">
        <h2 className="text-3xl font-bold text-white mb-6 text-center">Register</h2>
        {error && <div className="bg-red-500 text-white p-2 rounded mb-4 text-sm text-center">{error}</div>}
        <form onSubmit={handleRegister}>
          <div className="mb-4">
            <label className="block text-gray-300 text-sm font-bold mb-2">Full Name</label>
            <input 
              type="text" 
              className="w-full p-2 rounded bg-gray-700 text-white border border-gray-600 focus:border-indigo-500 outline-none"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              required
            />
          </div>
          <div className="mb-4">
            <label className="block text-gray-300 text-sm font-bold mb-2">Email Address</label>
            <input 
              type="email" 
              className="w-full p-2 rounded bg-gray-700 text-white border border-gray-600 focus:border-indigo-500 outline-none"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </div>
          <div className="mb-4">
            <label className="block text-gray-300 text-sm font-bold mb-2">Phone Number</label>
            <input 
              type="tel" 
              className="w-full p-2 rounded bg-gray-700 text-white border border-gray-600 focus:border-indigo-500 outline-none"
              value={phoneNumber}
              onChange={(e) => setPhoneNumber(e.target.value)}
              required
            />
          </div>
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
          <div className="mb-6">
            <label className="block text-gray-300 text-sm font-bold mb-2">Security Check: 2 + 2 = ?</label>
            <input 
              type="text" 
              className="w-full p-2 rounded bg-gray-700 text-white border border-gray-600 focus:border-indigo-500 outline-none"
              value={securityAnswer}
              onChange={(e) => setSecurityAnswer(e.target.value)}
              placeholder="Enter the result"
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
