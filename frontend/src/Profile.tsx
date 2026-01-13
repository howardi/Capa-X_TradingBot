import React, { useState, useEffect } from 'react';
import { User, Mail, Phone, Save } from 'lucide-react';

interface ProfileProps {
  username: string;
}

export const Profile = ({ username }: ProfileProps) => {
  const [profile, setProfile] = useState({
    username: '',
    email: '',
    full_name: '',
    phone_number: ''
  });
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState('');

  useEffect(() => {
    fetchProfile();
  }, [username]);

  const fetchProfile = async () => {
    try {
      const res = await fetch(`/api/user/profile?username=${username}`);
      if (res.ok) {
        const data = await res.json();
        setProfile({
          username: data.username || '',
          email: data.email || '',
          full_name: data.full_name || '',
          phone_number: data.phone_number || ''
        });
      }
    } catch (e) {
      console.error(e);
    }
    setLoading(false);
  };

  const handleUpdate = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const res = await fetch('/api/user/profile', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          username: profile.username,
          full_name: profile.full_name,
          phone_number: profile.phone_number
        })
      });
      if (res.ok) {
        setMessage('Profile updated successfully!');
        // Update local storage if needed
        const userStr = localStorage.getItem('user');
        if (userStr) {
            const user = JSON.parse(userStr);
            user.full_name = profile.full_name;
            user.phone_number = profile.phone_number;
            localStorage.setItem('user', JSON.stringify(user));
        }
      } else {
        setMessage('Failed to update profile.');
      }
    } catch (e) {
      setMessage('Network error.');
    }
  };

  if (loading) return <div className="text-white p-6">Loading profile...</div>;

  return (
    <div className="bg-gray-800 p-4 md:p-6 rounded-lg shadow-lg max-w-2xl mx-auto mt-4 md:mt-10 border border-gray-700">
      <h2 className="text-xl md:text-2xl font-bold text-white mb-6 flex items-center gap-2">
        <User className="text-indigo-400" /> User Profile
      </h2>
      
      {message && (
        <div className={`p-3 rounded mb-4 text-sm ${message.includes('success') ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'}`}>
          {message}
        </div>
      )}

      <form onSubmit={handleUpdate} className="space-y-4">
        <div>
          <label className="block text-gray-400 text-sm mb-1">Username</label>
          <input 
            type="text" 
            value={profile.username} 
            disabled 
            className="w-full bg-gray-700 text-gray-400 p-2 rounded border border-gray-600 cursor-not-allowed"
          />
        </div>

        <div>
          <label className="block text-gray-400 text-sm mb-1">Email Address</label>
          <div className="flex items-center gap-2 bg-gray-700 p-2 rounded border border-gray-600">
            <Mail size={16} className="text-gray-400" />
            <input 
              type="email" 
              value={profile.email} 
              disabled 
              className="bg-transparent text-gray-400 w-full outline-none cursor-not-allowed"
            />
          </div>
        </div>

        <div>
          <label className="block text-gray-300 text-sm mb-1">Full Name</label>
          <div className="flex items-center gap-2 bg-gray-900 p-2 rounded border border-gray-700 focus-within:border-indigo-500">
            <User size={16} className="text-gray-400" />
            <input 
              type="text" 
              value={profile.full_name} 
              onChange={(e) => setProfile({...profile, full_name: e.target.value})}
              className="bg-transparent text-white w-full outline-none"
              placeholder="John Doe"
            />
          </div>
        </div>

        <div>
          <label className="block text-gray-300 text-sm mb-1">Phone Number</label>
          <div className="flex items-center gap-2 bg-gray-900 p-2 rounded border border-gray-700 focus-within:border-indigo-500">
            <Phone size={16} className="text-gray-400" />
            <input 
              type="tel" 
              value={profile.phone_number} 
              onChange={(e) => setProfile({...profile, phone_number: e.target.value})}
              className="bg-transparent text-white w-full outline-none"
              placeholder="+1 234 567 8900"
            />
          </div>
        </div>

        <button 
          type="submit" 
          className="w-full bg-indigo-600 hover:bg-indigo-700 text-white font-bold py-2 px-4 rounded transition flex items-center justify-center gap-2"
        >
          <Save size={18} /> Save Changes
        </button>
      </form>
    </div>
  );
};
