import React, { useState, useEffect, useCallback } from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { toast } from 'sonner';
import { FiSearch, FiLoader, FiEdit2, FiTrash2, FiRefreshCw } from 'react-icons/fi';
import { formatDistanceToNow, parseISO } from 'date-fns';
import { quoteRequestsApi } from '@/lib/api';

const STATUS_COLORS = {
  pending: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300',
  contacted: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300',
  converted: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300',
  cancelled: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300',
};

const STATUS_OPTIONS = [
  { value: 'all', label: 'All Statuses' },
  { value: 'pending', label: 'Pending Review' },
  { value: 'contacted', label: 'Customer Contacted' },
  { value: 'converted', label: 'Converted to Quote' },
  { value: 'cancelled', label: 'Cancelled' },
];

function QuoteRequestsPage() {
  const [requests, setRequests] = useState([]);
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState('all');
  const [search, setSearch] = useState('');

  const fetchRequests = useCallback(async () => {
    setLoading(true);
    try {
      const params = {};
      if (status !== 'all') params.status = status;
      if (search) params.search = search;
      const { data } = await quoteRequestsApi.list(params);
      setRequests(data.results || data);
    } catch {
      toast.error('Failed to fetch quote requests');
    } finally {
      setLoading(false);
    }
  }, [status, search]);

  useEffect(() => {
    fetchRequests();
  }, [fetchRequests]);

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold mb-4">Quote Requests</h1>
      <div className="flex gap-2 mb-4">
        <Input
          placeholder="Search by customer, location, or request ID..."
          value={search}
          onChange={e => setSearch(e.target.value)}
          className="max-w-xs"
        />
        <select value={status} onChange={e => setStatus(e.target.value)} className="border rounded px-2 py-1">
          {STATUS_OPTIONS.map(opt => (
            <option key={opt.value} value={opt.value}>{opt.label}</option>
          ))}
        </select>
        <Button onClick={fetchRequests} disabled={loading} variant="outline">
          {loading ? <FiLoader className="animate-spin" /> : <FiRefreshCw />} Refresh
        </Button>
      </div>
      <Card>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Request ID</TableHead>
                <TableHead>Customer</TableHead>
                <TableHead>Gadgets</TableHead>
                <TableHead>Roof Type</TableHead>
                <TableHead>Location</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Created</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {requests.map(req => (
                <TableRow key={req.id}>
                  <TableCell>{req.request_id}</TableCell>
                  <TableCell>{req.customer_name_display}</TableCell>
                  <TableCell>{req.gadgets_to_power || '—'}</TableCell>
                  <TableCell>{req.roof_type || '—'}</TableCell>
                  <TableCell>{req.location || '—'}</TableCell>
                  <TableCell>
                    <span className={`px-2 py-1 rounded text-xs font-medium ${STATUS_COLORS[req.status] || ''}`}>{req.status}</span>
                  </TableCell>
                  <TableCell>{formatDistanceToNow(parseISO(req.created_at), { addSuffix: true })}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}

export default QuoteRequestsPage;
