import React, { useState, useEffect, useCallback } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { toast } from 'sonner';
import { FiSearch, FiLoader, FiEdit2, FiTrash2, FiEye, FiRefreshCw } from 'react-icons/fi';
import { formatDistanceToNow, parseISO } from 'date-fns';
import { productOrdersApi } from '@/lib/api';
import { useDebounce } from 'use-debounce';

const STATUS_COLORS = {
  pending: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300',
  confirmed: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300',
  processing: 'bg-indigo-100 text-indigo-800 dark:bg-indigo-900/30 dark:text-indigo-300',
  shipped: 'bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-300',
  delivered: 'bg-teal-100 text-teal-800 dark:bg-teal-900/30 dark:text-teal-300',
  completed: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300',
  cancelled: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300',
};

const STATUS_OPTIONS = [
  { value: '', label: 'All Statuses' },
  { value: 'pending', label: 'Pending Review' },
  { value: 'confirmed', label: 'Confirmed' },
  { value: 'processing', label: 'Processing' },
  { value: 'shipped', label: 'Shipped' },
  { value: 'delivered', label: 'Delivered' },
  { value: 'completed', label: 'Completed' },
  { value: 'cancelled', label: 'Cancelled' },
];

function OrderDetailDialog({ order, open, onClose, onUpdated }) {
  const [status, setStatus] = useState(order?.status || 'pending');
  const [notes, setNotes] = useState(order?.internal_notes || '');
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (order) {
      setStatus(order.status);
      setNotes(order.internal_notes || '');
    }
  }, [order]);

  if (!order) return null;

  const handleSave = async () => {
    setSaving(true);
    try {
      await productOrdersApi.update(order.id, { status, internal_notes: notes });
      toast.success('Order updated');
      onUpdated();
      onClose();
    } catch {
      toast.error('Failed to update order');
    } finally {
      setSaving(false);
    }
  };

  const waLink = `https://wa.me/${(order.customer_phone || '').replace(/\D/g, '')}`;

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>Order {order.order_number}</DialogTitle>
        </DialogHeader>
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div><span className="font-medium text-muted-foreground">Customer:</span> <span>{order.customer_name}</span></div>
          <div><span className="font-medium text-muted-foreground">Phone:</span>
            <a href={`tel:${order.customer_phone}`} className="ml-1 text-blue-600 hover:underline">{order.customer_phone}</a>
            {order.customer_phone && (
              <a href={waLink} target="_blank" rel="noopener noreferrer" className="ml-2 text-green-600 hover:underline text-xs">[WhatsApp]</a>
            )}
          </div>
          <div><span className="font-medium text-muted-foreground">Product:</span> <span>{order.product_name}</span></div>
          <div><span className="font-medium text-muted-foreground">Qty:</span> <span>{order.quantity}</span></div>
          <div><span className="font-medium text-muted-foreground">Total:</span> <span>{order.currency} {Number(order.total_price).toFixed(2)}</span></div>
          <div><span className="font-medium text-muted-foreground">Delivery:</span> <span className="capitalize">{order.delivery_method?.replace(/_/g, ' ')}</span></div>
          {order.delivery_address && (
            <div className="col-span-2"><span className="font-medium text-muted-foreground">Delivery Address:</span> <span>{order.delivery_address}</span></div>
          )}
          {order.customer_notes && (
            <div className="col-span-2"><span className="font-medium text-muted-foreground">Customer Notes:</span> <span>{order.customer_notes}</span></div>
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
            {saving ? <FiLoader className="animate-spin mr-2 h-4 w-4" /> : null}Save Changes
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function DeleteConfirmDialog({ open, onClose, onConfirm, orderNumber }) {
  const [deleting, setDeleting] = useState(false);
  const handleConfirm = async () => {
    setDeleting(true);
    await onConfirm();
    setDeleting(false);
  };
  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent>
        <DialogHeader><DialogTitle>Delete Order</DialogTitle></DialogHeader>
        <p className="text-sm text-muted-foreground">Are you sure you want to delete order <strong>{orderNumber}</strong>? This action cannot be undone.</p>
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>Cancel</Button>
          <Button variant="destructive" onClick={handleConfirm} disabled={deleting}>
            {deleting ? <FiLoader className="animate-spin mr-2 h-4 w-4" /> : null}Delete
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export default function OrdersPage() {
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [debouncedSearch] = useDebounce(search, 300);
  const [statusFilter, setStatusFilter] = useState('');
  const [selectedOrder, setSelectedOrder] = useState(null);
  const [deleteTarget, setDeleteTarget] = useState(null);
  const [viewDialog, setViewDialog] = useState(false);

  const fetchOrders = useCallback(async () => {
    setLoading(true);
    try {
      const params = {};
      if (debouncedSearch) params.search = debouncedSearch;
      if (statusFilter) params.status = statusFilter;
      const res = await productOrdersApi.list(params);
      setOrders(res.data.results || res.data || []);
    } catch {
      toast.error("Failed to load orders");
    } finally {
      setLoading(false);
    }
  }, [debouncedSearch, statusFilter]);

  useEffect(() => { fetchOrders(); }, [fetchOrders]);

  const handleDelete = async () => {
    try {
      await productOrdersApi.delete(deleteTarget.id);
      toast.success('Order deleted');
      setDeleteTarget(null);
      fetchOrders();
    } catch {
      toast.error('Failed to delete order');
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Orders</h1>
        <Button variant="outline" size="sm" onClick={fetchOrders}>
          <FiRefreshCw className="mr-2 h-4 w-4" />Refresh
        </Button>
      </div>

      <Card className="dark:bg-slate-800">
        <CardContent className="p-4">
          <div className="flex flex-col sm:flex-row gap-3 mb-4">
            <div className="relative flex-1">
              <FiSearch className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input placeholder="Search orders, customers..." className="pl-9" value={search} onChange={e => setSearch(e.target.value)} />
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
          ) : orders.length === 0 ? (
            <div className="text-center py-12 text-muted-foreground">No orders found</div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Order #</TableHead>
                  <TableHead>Customer</TableHead>
                  <TableHead>Product</TableHead>
                  <TableHead>Total</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Date</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {orders.map(order => (
                  <TableRow key={order.id}>
                    <TableCell className="font-mono text-xs">{order.order_number}</TableCell>
                    <TableCell>
                      <div className="font-medium">{order.customer_name}</div>
                      <div className="text-xs text-muted-foreground">{order.customer_phone}</div>
                    </TableCell>
                    <TableCell>
                      <div>{order.product_name}</div>
                      <div className="text-xs text-muted-foreground">x{order.quantity}</div>
                    </TableCell>
                    <TableCell>{order.currency} {Number(order.total_price).toFixed(2)}</TableCell>
                    <TableCell>
                      <span className={`inline-flex px-2 py-1 rounded-full text-xs font-medium ${STATUS_COLORS[order.status] || ''}`}>
                        {order.status}
                      </span>
                    </TableCell>
                    <TableCell className="text-xs text-muted-foreground">
                      {order.created_at ? formatDistanceToNow(parseISO(order.created_at), { addSuffix: true }) : '—'}
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex items-center justify-end gap-1">
                        <Button variant="ghost" size="icon" onClick={() => { setSelectedOrder(order); setViewDialog(true); }}>
                          <FiEdit2 className="h-4 w-4" />
                        </Button>
                        <Button variant="ghost" size="icon" onClick={() => setDeleteTarget(order)} className="text-red-500 hover:text-red-700">
                          <FiTrash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      <OrderDetailDialog
        order={selectedOrder}
        open={viewDialog}
        onClose={() => setViewDialog(false)}
        onUpdated={fetchOrders}
      />
      <DeleteConfirmDialog
        open={!!deleteTarget}
        onClose={() => setDeleteTarget(null)}
        onConfirm={handleDelete}
        orderNumber={deleteTarget?.order_number}
      />
    </div>
  );
}

