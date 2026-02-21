import React, { useState, useEffect, useCallback } from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { toast } from 'sonner';
import { FiSearch, FiLoader, FiEdit2, FiTrash2, FiRefreshCw, FiMapPin, FiPhone } from 'react-icons/fi';
import { BsWhatsapp } from 'react-icons/bs';
import { formatDistanceToNow, parseISO } from 'date-fns';
import { installationRequestsApi } from '@/lib/api';
import { useDebounce } from 'use-debounce';

const STATUS_COLORS = {
  pending: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300',
  contacted: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300',
  scheduled: 'bg-indigo-100 text-indigo-800 dark:bg-indigo-900/30 dark:text-indigo-300',
  completed: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300',
  cancelled: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300',
};

const STATUS_OPTIONS = [
  { value: '', label: 'All Statuses' },
  { value: 'pending', label: 'Pending Review' },
  { value: 'contacted', label: 'Customer Contacted' },
  { value: 'scheduled', label: 'Installation Scheduled' },
  { value: 'completed', label: 'Completed' },
  { value: 'cancelled', label: 'Cancelled' },
];

function getMapUrl(req) {
  if (req.location_pin && req.location_pin.latitude && req.location_pin.longitude) {
    return `https://www.google.com/maps?q=${req.location_pin.latitude},${req.location_pin.longitude}`;
  }
  if (req.installation_address) {
    return `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(req.installation_address)}`;
  }
  return null;
}

function RequestDetailDialog({ request, open, onClose, onUpdated }) {
  const [status, setStatus] = useState(request?.status || 'pending');
  const [notes, setNotes] = useState(request?.notes || '');
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (request) {
      setStatus(request.status);
      setNotes(request.notes || '');
    }
  }, [request]);

  if (!request) return null;

  const mapUrl = getMapUrl(request);
  const whatsappPhone = (request.contact_whatsapp_id || request.contact_phone || '').replace(/\D/g, '');

  const handleSave = async () => {
    setSaving(true);
    try {
      await installationRequestsApi.update(request.id, { status, notes });
      toast.success('Installation request updated');
      onUpdated();
      onClose();
    } catch {
      toast.error('Failed to update request');
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>Installation Request {request.request_id}</DialogTitle>
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
          <div><span className="font-medium text-muted-foreground">System Size:</span> <span>{request.system_size || '—'}</span></div>
          <div><span className="font-medium text-muted-foreground">Payment:</span> <span>{request.payment_preference || '—'}</span></div>
          <div><span className="font-medium text-muted-foreground">Preferred Date:</span> <span>{request.preferred_date || '—'}</span></div>
          <div><span className="font-medium text-muted-foreground">Time:</span> <span>{request.time_preference || '—'}</span></div>
          {request.installation_address && (
            <div className="col-span-2 flex items-start gap-2">
              <span className="font-medium text-muted-foreground flex-shrink-0">Address:</span>
              <span className="flex-1">{request.installation_address}</span>
              {mapUrl && (
                <a href={mapUrl} target="_blank" rel="noopener noreferrer"
                  className="flex items-center gap-1 text-blue-600 hover:underline text-xs flex-shrink-0">
                  <FiMapPin className="h-3.5 w-3.5" />View Map
                </a>
              )}
            </div>
          )}
          {request.additional_notes && (
            <div className="col-span-2"><span className="font-medium text-muted-foreground">Notes:</span> <span>{request.additional_notes}</span></div>
          )}
        </div>

        <div className="space-y-3 mt-2">
          <div className="space-y-1">
            <Label>Status</Label>
            <Select value={status} onValueChange={setStatus}>
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>
                {STATUS_OPTIONS.filter(o => o.value).map(o => (
                  <SelectItem key={o.value} value={o.value}>{o.label}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-1">
            <Label>Internal Notes</Label>
            <Textarea value={notes} onChange={e => setNotes(e.target.value)} rows={3} placeholder="Add internal notes..." />
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>Cancel</Button>
          <Button onClick={handleSave} disabled={saving}>
            {saving && <FiLoader className="animate-spin mr-2 h-4 w-4" />}Save Changes
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function DeleteConfirmDialog({ open, onClose, onConfirm, requestId }) {
  const [deleting, setDeleting] = useState(false);
  const handleConfirm = async () => {
    setDeleting(true);
    await onConfirm();
    setDeleting(false);
  };
  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent>
        <DialogHeader><DialogTitle>Delete Installation Request</DialogTitle></DialogHeader>
        <p className="text-sm text-muted-foreground">Delete request <strong>{requestId}</strong>? This cannot be undone.</p>
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>Cancel</Button>
          <Button variant="destructive" onClick={handleConfirm} disabled={deleting}>
            {deleting && <FiLoader className="animate-spin mr-2 h-4 w-4" />}Delete
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export default function InstallationRequestsPage() {
  const [requests, setRequests] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [debouncedSearch] = useDebounce(search, 300);
  const [statusFilter, setStatusFilter] = useState('');
  const [selected, setSelected] = useState(null);
  const [deleteTarget, setDeleteTarget] = useState(null);

  const fetchRequests = useCallback(async () => {
    setLoading(true);
    try {
      const params = {};
      if (debouncedSearch) params.search = debouncedSearch;
      if (statusFilter) params.status = statusFilter;
      const res = await installationRequestsApi.list(params);
      setRequests(res.data.results || res.data || []);
    } catch {
      toast.error("Failed to load installation requests");
    } finally {
      setLoading(false);
    }
  }, [debouncedSearch, statusFilter]);

  useEffect(() => { fetchRequests(); }, [fetchRequests]);

  const handleDelete = async () => {
    try {
      await installationRequestsApi.delete(deleteTarget.id);
      toast.success('Request deleted');
      setDeleteTarget(null);
      fetchRequests();
    } catch {
      toast.error('Failed to delete request');
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Installation Requests</h1>
        <Button variant="outline" size="sm" onClick={fetchRequests}>
          <FiRefreshCw className="mr-2 h-4 w-4" />Refresh
        </Button>
      </div>

      <Card className="dark:bg-slate-800">
        <CardContent className="p-4">
          <div className="flex flex-col sm:flex-row gap-3 mb-4">
            <div className="relative flex-1">
              <FiSearch className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input placeholder="Search by customer or address..." className="pl-9" value={search} onChange={e => setSearch(e.target.value)} />
            </div>
            <Select value={statusFilter} onValueChange={setStatusFilter}>
              <SelectTrigger className="w-full sm:w-48">
                <SelectValue placeholder="Filter by status" />
              </SelectTrigger>
              <SelectContent>
                {STATUS_OPTIONS.map(o => (
                  <SelectItem key={o.value || 'all'} value={o.value}>{o.label}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {loading ? (
            <div className="flex justify-center py-12"><FiLoader className="animate-spin h-6 w-6 text-muted-foreground" /></div>
          ) : requests.length === 0 ? (
            <div className="text-center py-12 text-muted-foreground">No installation requests found</div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Request ID</TableHead>
                  <TableHead>Customer</TableHead>
                  <TableHead>System</TableHead>
                  <TableHead>Date Pref.</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {requests.map(req => {
                  const mapUrl = getMapUrl(req);
                  const wp = (req.contact_whatsapp_id || req.contact_phone || '').replace(/\D/g, '');
                  return (
                    <TableRow key={req.id}>
                      <TableCell className="font-mono text-xs">{req.request_id}</TableCell>
                      <TableCell>
                        <div className="font-medium">{req.customer_name_display}</div>
                        <div className="flex items-center gap-1 mt-0.5">
                          {req.contact_phone && (
                            <a href={`tel:${req.contact_phone}`} className="text-blue-500 hover:text-blue-700" title="Call">
                              <FiPhone className="h-3.5 w-3.5" />
                            </a>
                          )}
                          {wp && (
                            <a href={`https://wa.me/${wp}`} target="_blank" rel="noopener noreferrer" className="text-green-500 hover:text-green-700" title="WhatsApp">
                              <BsWhatsapp className="h-3.5 w-3.5" />
                            </a>
                          )}
                          {mapUrl && (
                            <a href={mapUrl} target="_blank" rel="noopener noreferrer" className="text-orange-500 hover:text-orange-700" title="View Map">
                              <FiMapPin className="h-3.5 w-3.5" />
                            </a>
                          )}
                        </div>
                      </TableCell>
                      <TableCell>{req.system_size || '—'}</TableCell>
                      <TableCell className="text-xs">{req.preferred_date || '—'}</TableCell>
                      <TableCell>
                        <span className={`inline-flex px-2 py-1 rounded-full text-xs font-medium ${STATUS_COLORS[req.status] || ''}`}>
                          {req.status}
                        </span>
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-1">
                          <Button variant="ghost" size="icon" onClick={() => setSelected(req)}>
                            <FiEdit2 className="h-4 w-4" />
                          </Button>
                          <Button variant="ghost" size="icon" onClick={() => setDeleteTarget(req)} className="text-red-500 hover:text-red-700">
                            <FiTrash2 className="h-4 w-4" />
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      <RequestDetailDialog
        request={selected}
        open={!!selected}
        onClose={() => setSelected(null)}
        onUpdated={fetchRequests}
      />
      <DeleteConfirmDialog
        open={!!deleteTarget}
        onClose={() => setDeleteTarget(null)}
        onConfirm={handleDelete}
        requestId={deleteTarget?.request_id}
      />
    </div>
  );
}

