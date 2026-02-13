import React from 'react';
import { Link } from 'react-router-dom';
import { FiUsers, FiMessageCircle, FiBarChart2, FiActivity, FiCreditCard, FiSettings } from 'react-icons/fi';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { useAuth } from '@/context/AuthContext';

const StatCard = ({ title, value, icon, linkTo, colorScheme }) => {
  const colors = {
    green: { bg: 'bg-green-50 dark:bg-green-900/40', border: 'border-green-500/60', text: 'text-green-700 dark:text-green-300', iconColor: 'text-green-600 dark:text-green-400' },
    emerald: { bg: 'bg-emerald-50 dark:bg-emerald-900/40', border: 'border-emerald-500/60', text: 'text-emerald-700 dark:text-emerald-300', iconColor: 'text-emerald-600 dark:text-emerald-400' },
    teal: { bg: 'bg-teal-50 dark:bg-teal-900/40', border: 'border-teal-500/60', text: 'text-teal-700 dark:text-teal-300', iconColor: 'text-teal-600 dark:text-teal-400' },
    red: { bg: 'bg-red-50 dark:bg-red-900/40', border: 'border-red-500/60', text: 'text-red-700 dark:text-red-300', iconColor: 'text-red-600 dark:text-red-400' },
  };
  const c = colors[colorScheme] || colors.green;
  const content = (
    <div className={`p-5 rounded-xl shadow-lg border-l-4 ${c.border} ${c.bg} flex flex-col justify-between min-h-[140px] h-full transition-transform hover:scale-[1.02] cursor-pointer`}>
      <div className="flex items-center justify-between mb-1">
        <h3 className="text-sm font-semibold text-gray-600 dark:text-gray-300">{title}</h3>
        {React.cloneElement(icon, { className: `h-6 w-6 opacity-70 ${c.iconColor}` })}
      </div>
      <p className={`text-3xl font-bold ${c.text}`}>{value}</p>
    </div>
  );
  return linkTo ? <Link to={linkTo} className="block h-full">{content}</Link> : <div className="block h-full">{content}</div>;
};

export default function Dashboard() {
  const { user } = useAuth();

  return (
    <div className="space-y-8 pb-12">
      <div>
        <h1 className="text-2xl md:text-3xl font-bold text-gray-800 dark:text-gray-100">Dashboard Overview</h1>
        <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">
          Welcome{user?.username ? `, ${user.username}` : ''}! Here's a summary of your Sungrip Solar CRM activity.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
        <StatCard title="Active Conversations" value="—" icon={<FiMessageCircle />} linkTo="/conversation" colorScheme="green" />
        <StatCard title="Total Contacts" value="—" icon={<FiUsers />} linkTo="/contacts" colorScheme="emerald" />
        <StatCard title="Pending Orders" value="—" icon={<FiCreditCard />} linkTo="/orders" colorScheme="teal" />
        <StatCard title="Installation Requests" value="—" icon={<FiActivity />} linkTo="/installation-requests" colorScheme="red" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card className="dark:bg-slate-800 dark:border-slate-700 shadow-lg">
          <CardHeader>
            <CardTitle className="text-lg font-semibold dark:text-slate-100 flex items-center">
              <FiBarChart2 className="mr-2 text-green-500" /> Quick Actions
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <Link to="/conversation" className="flex items-center justify-between p-3 rounded-lg bg-slate-50 dark:bg-slate-700/50 hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors cursor-pointer">
              <div className="flex items-center"><FiMessageCircle className="h-5 w-5 mr-3 text-green-500" /><span className="text-sm font-medium">Reply to Messages</span></div>
            </Link>
            <Link to="/contacts" className="flex items-center justify-between p-3 rounded-lg bg-slate-50 dark:bg-slate-700/50 hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors cursor-pointer">
              <div className="flex items-center"><FiUsers className="h-5 w-5 mr-3 text-emerald-500" /><span className="text-sm font-medium">Manage Contacts</span></div>
            </Link>
            <Link to="/api-settings" className="flex items-center justify-between p-3 rounded-lg bg-slate-50 dark:bg-slate-700/50 hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors cursor-pointer">
              <div className="flex items-center"><FiSettings className="h-5 w-5 mr-3 text-teal-500" /><span className="text-sm font-medium">Configure WhatsApp API</span></div>
            </Link>
          </CardContent>
        </Card>

        <Card className="dark:bg-slate-800 dark:border-slate-700 shadow-lg">
          <CardHeader>
            <CardTitle className="text-lg font-semibold dark:text-slate-100 flex items-center">
              <FiActivity className="mr-2 text-blue-500" /> Recent Activity
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-slate-500 dark:text-slate-400 italic p-3 text-center">
              Activity feed will populate once the backend is connected.
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
