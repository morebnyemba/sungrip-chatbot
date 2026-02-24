import React, { useState, useEffect, useCallback } from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { toast } from 'sonner';
import { FiSearch, FiLoader, FiRefreshCw, FiPhone } from 'react-icons/fi';
import { BsWhatsapp } from 'react-icons/bs';
function getWhatsappPhone(request) {
  return (request.contact_whatsapp_id || request.contact_phone || '').replace(/\D/g, '');
}

function RequestDetailDialog({ request, open, onClose }) {
  if (!request) return null;
  const whatsappPhone = getWhatsappPhone(request);
  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>Quote Request {request.request_id}</DialogTitle>
        </DialogHeader>
        <div className="grid grid-cols-2 gap-3 text-sm">
          <div><span className="font-medium text-muted-foreground">Customer:</span> <span>{request.customer_name_display}</span></div>
          <div className="flex items-center gap-2">
            <span className="font-medium text-muted-foreground">Contact:</span>
            {request.contact_phone && (
              <a href={`tel:${request.contact_phone}`} className="text-blue-600 hover:underline flex items-center gap-1">
                <FiPhone className="h-3.5 w-3.5" />{request.contact_phone}
              </a>
            )}
            {whatsappPhone && (
              <a href={`https://wa.me/${whatsappPhone}`} target="_blank" rel="noopener noreferrer" className="text-green-600 hover:underline flex items-center gap-1">
                <BsWhatsapp className="h-3.5 w-3.5" />WhatsApp
              </a>
            )}
          </div>
          <div><span className="font-medium text-muted-foreground">Gadgets:</span> <span>{request.gadgets_to_power || '—'}</span></div>
          <div><span className="font-medium text-muted-foreground">Roof Type:</span> <span>{request.roof_type || '—'}</span></div>
          <div><span className="font-medium text-muted-foreground">Location:</span> <span>{request.location || '—'}</span></div>
          <div><span className="font-medium text-muted-foreground">Status:</span> <span>{request.status}</span></div>
        </div>
        <DialogFooter>
          <Button variant="ghost" onClick={onClose}>Close</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
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
  const [selectedRequest, setSelectedRequest] = useState(null);

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
                <TableRow key={req.id} className="cursor-pointer hover:bg-gray-50 dark:hover:bg-slate-800" onClick={() => setSelectedRequest(req)}>
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
      <RequestDetailDialog request={selectedRequest} open={!!selectedRequest} onClose={() => setSelectedRequest(null)} />
    </div>
  );
}

export default QuoteRequestsPage;
