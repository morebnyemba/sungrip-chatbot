import React, { useState, useEffect } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { toast } from 'sonner';
import { FiBarChart2, FiLoader, FiRefreshCw, FiMessageCircle, FiUsers, FiActivity, FiCreditCard } from 'react-icons/fi';
import { dashboardStatsApi, webhookLogsApi } from '@/lib/api';
import { formatDistanceToNow, parseISO } from 'date-fns';

const EVENT_COLORS = {
  message: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300',
  message_status: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300',
  flow_response: 'bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-300',
  error: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300',
};

export default function AnalyticsPage() {
  const [stats, setStats] = useState(null);
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [statsRes, logsRes] = await Promise.all([
        dashboardStatsApi.get(),
        webhookLogsApi.list({ page_size: 20, ordering: '-received_at' }),
      ]);
      setStats(statsRes.data);
      setLogs(logsRes.data.results || logsRes.data || []);
    } catch {
      toast.error('Failed to load analytics data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchData(); }, []);

  if (loading) {
    return <div className="flex justify-center py-20"><FiLoader className="animate-spin h-8 w-8 text-muted-foreground" /></div>;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Analytics</h1>
        <Button variant="outline" size="sm" onClick={fetchData}><FiRefreshCw className="mr-2 h-4 w-4" />Refresh</Button>
      </div>

      {stats && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <Card className="dark:bg-slate-800">
            <CardContent className="p-4 flex items-center gap-3">
              <div className="rounded-full bg-green-100 dark:bg-green-900/40 p-3"><FiMessageCircle className="h-5 w-5 text-green-600" /></div>
              <div><p className="text-sm text-muted-foreground">Active Conversations</p><p className="text-2xl font-bold">{stats.active_conversations}</p></div>
            </CardContent>
          </Card>
          <Card className="dark:bg-slate-800">
            <CardContent className="p-4 flex items-center gap-3">
              <div className="rounded-full bg-emerald-100 dark:bg-emerald-900/40 p-3"><FiUsers className="h-5 w-5 text-emerald-600" /></div>
              <div><p className="text-sm text-muted-foreground">Total Contacts</p><p className="text-2xl font-bold">{stats.total_contacts}</p></div>
            </CardContent>
          </Card>
          <Card className="dark:bg-slate-800">
            <CardContent className="p-4 flex items-center gap-3">
              <div className="rounded-full bg-teal-100 dark:bg-teal-900/40 p-3"><FiCreditCard className="h-5 w-5 text-teal-600" /></div>
              <div><p className="text-sm text-muted-foreground">Pending Orders</p><p className="text-2xl font-bold">{stats.pending_orders}</p></div>
            </CardContent>
          </Card>
          <Card className="dark:bg-slate-800">
            <CardContent className="p-4 flex items-center gap-3">
              <div className="rounded-full bg-red-100 dark:bg-red-900/40 p-3"><FiActivity className="h-5 w-5 text-red-600" /></div>
              <div><p className="text-sm text-muted-foreground">Installation Requests</p><p className="text-2xl font-bold">{stats.installation_requests}</p></div>
            </CardContent>
          </Card>
        </div>
      )}

      <Card className="dark:bg-slate-800">
        <CardHeader>
          <CardTitle className="flex items-center text-lg"><FiBarChart2 className="mr-2 text-blue-500" />Recent Webhook Events</CardTitle>
        </CardHeader>
        <CardContent>
          {logs.length === 0 ? (
            <p className="text-center py-8 text-muted-foreground">No webhook events recorded yet.</p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Type</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Phone Number ID</TableHead>
                  <TableHead>Received</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {logs.map(log => (
                  <TableRow key={log.id}>
                    <TableCell>
                      <Badge className={EVENT_COLORS[log.event_type] || 'bg-gray-100 text-gray-800'}>
                        {log.event_type?.replace(/_/g, ' ')}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-sm">{log.processing_status || '—'}</TableCell>
                    <TableCell className="font-mono text-xs">{log.phone_number_id_received || '—'}</TableCell>
                    <TableCell className="text-xs text-muted-foreground">
                      {log.received_at ? formatDistanceToNow(parseISO(log.received_at), { addSuffix: true }) : '—'}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
