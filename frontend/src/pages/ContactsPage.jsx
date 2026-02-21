import React, { useState, useEffect, useCallback } from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { toast } from 'sonner';
import { FiSearch, FiLoader, FiEdit2, FiTrash2, FiRefreshCw, FiPhone, FiMapPin, FiAlertCircle } from 'react-icons/fi';
import { BsWhatsapp } from 'react-icons/bs';
import { formatDistanceToNow, parseISO } from 'date-fns';
import { customersApi } from '@/lib/api';
import { useDebounce } from 'use-debounce';

const CUSTOMER_TYPE_OPTIONS = [
  { value: 'residential', label: 'Residential' },
  { value: 'commercial', label: 'Commercial' },
  { value: 'industrial', label: 'Industrial' },
];

function getMapUrl(customer) {
  if (customer.gps_latitude && customer.gps_longitude) {
    return `https://www.google.com/maps?q=${customer.gps_latitude},${customer.gps_longitude}`;
  }
  const address = [customer.address_line1, customer.city, customer.province].filter(Boolean).join(', ');
  if (address) {
    return `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(address)}`;
  }
  return null;
}

function CustomerFormDialog({ customer, open, onClose, onSaved }) {
  const isEdit = !!customer?.id;
  const [form, setForm] = useState({
    full_name: '', phone_number: '', whatsapp_number: '', email: '',
    address_line1: '', city: '', province: '', postal_code: '',
    customer_type: 'residential', notes: '', is_active: true,
  });
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (customer) {
      setForm({
        full_name: customer.full_name || '',
        phone_number: customer.phone_number || '',
        whatsapp_number: customer.whatsapp_number || '',
        email: customer.email || '',
        address_line1: customer.address_line1 || '',
        city: customer.city || '',
        province: customer.province || '',
        postal_code: customer.postal_code || '',
        customer_type: customer.customer_type || 'residential',
        notes: customer.notes || '',
        is_active: customer.is_active ?? true,
      });
    } else {
      setForm({ full_name: '', phone_number: '', whatsapp_number: '', email: '', address_line1: '', city: '', province: '', postal_code: '', customer_type: 'residential', notes: '', is_active: true });
    }
  }, [customer]);

  const set = (field) => (e) => setForm(prev => ({ ...prev, [field]: e.target?.value ?? e }));

  const handleSave = async () => {
    if (!form.full_name || !form.phone_number) {
      toast.error('Name and phone number are required');
      return;
    }
    setSaving(true);
    try {
      if (isEdit) {
        await customersApi.update(customer.id, form);
        toast.success('Customer updated');
      } else {
        await customersApi.create(form);
        toast.success('Customer created');
      }
      onSaved();
      onClose();
    } catch (err) {
      const msg = err.response?.data ? JSON.stringify(err.response.data) : 'Failed to save';
      toast.error(msg);
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{isEdit ? 'Edit Customer' : 'New Customer'}</DialogTitle>
        </DialogHeader>
        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-1 col-span-2 sm:col-span-1">
            <Label>Full Name *</Label>
            <Input value={form.full_name} onChange={set('full_name')} placeholder="Full Name" />
          </div>
          <div className="space-y-1 col-span-2 sm:col-span-1">
            <Label>Phone Number *</Label>
            <Input value={form.phone_number} onChange={set('phone_number')} placeholder="+263771234567" />
          </div>
          <div className="space-y-1 col-span-2 sm:col-span-1">
            <Label>WhatsApp Number</Label>
            <Input value={form.whatsapp_number} onChange={set('whatsapp_number')} placeholder="+263771234567" />
          </div>
          <div className="space-y-1 col-span-2 sm:col-span-1">
            <Label>Email</Label>
            <Input type="email" value={form.email} onChange={set('email')} placeholder="email@example.com" />
          </div>
          <div className="space-y-1 col-span-2">
            <Label>Address</Label>
            <Input value={form.address_line1} onChange={set('address_line1')} placeholder="Street address" />
          </div>
          <div className="space-y-1">
            <Label>City</Label>
            <Input value={form.city} onChange={set('city')} placeholder="City" />
          </div>
          <div className="space-y-1">
            <Label>Province</Label>
            <Input value={form.province} onChange={set('province')} placeholder="Province" />
          </div>
          <div className="space-y-1">
            <Label>Customer Type</Label>
            <Select value={form.customer_type} onValueChange={set('customer_type')}>
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>
                {CUSTOMER_TYPE_OPTIONS.map(o => <SelectItem key={o.value} value={o.value}>{o.label}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-1">
            <Label>Status</Label>
            <Select value={form.is_active ? 'active' : 'inactive'} onValueChange={v => setForm(prev => ({ ...prev, is_active: v === 'active' }))}>
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="active">Active</SelectItem>
                <SelectItem value="inactive">Inactive</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-1 col-span-2">
            <Label>Notes</Label>
            <Textarea value={form.notes} onChange={set('notes')} rows={3} placeholder="Internal notes..." />
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>Cancel</Button>
          <Button onClick={handleSave} disabled={saving}>
            {saving && <FiLoader className="animate-spin mr-2 h-4 w-4" />}
            {isEdit ? 'Update' : 'Create'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function DeleteConfirmDialog({ open, onClose, onConfirm, customerName }) {
  const [deleting, setDeleting] = useState(false);
  const handleConfirm = async () => {
    setDeleting(true);
    await onConfirm();
    setDeleting(false);
  };
  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent>
        <DialogHeader><DialogTitle>Delete Customer</DialogTitle></DialogHeader>
        <p className="text-sm text-muted-foreground">Delete <strong>{customerName}</strong>? This cannot be undone.</p>
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

export default function ContactsPage() {
  const [customers, setCustomers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [debouncedSearch] = useDebounce(search, 300);
  const [typeFilter, setTypeFilter] = useState('');
  const [formCustomer, setFormCustomer] = useState(null);
  const [formOpen, setFormOpen] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState(null);

  const fetchCustomers = useCallback(async () => {
    setLoading(true);
    try {
      const params = {};
      if (debouncedSearch) params.search = debouncedSearch;
      if (typeFilter) params.customer_type = typeFilter;
      const res = await customersApi.list(params);
      setCustomers(res.data.results || res.data || []);
    } catch {
      toast.error("Failed to load customers");
    } finally {
      setLoading(false);
    }
  }, [debouncedSearch, typeFilter]);

  useEffect(() => { fetchCustomers(); }, [fetchCustomers]);

  const openCreate = () => { setFormCustomer(null); setFormOpen(true); };
  const openEdit = (c) => { setFormCustomer(c); setFormOpen(true); };

  const handleDelete = async () => {
    try {
      await customersApi.delete(deleteTarget.id);
      toast.success('Customer deleted');
      setDeleteTarget(null);
      fetchCustomers();
    } catch {
      toast.error('Failed to delete customer');
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Customer Profiles</h1>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={fetchCustomers}>
            <FiRefreshCw className="mr-2 h-4 w-4" />Refresh
          </Button>
          <Button size="sm" onClick={openCreate}>+ New Customer</Button>
        </div>
      </div>

      <Card className="dark:bg-slate-800">
        <CardContent className="p-4">
          <div className="flex flex-col sm:flex-row gap-3 mb-4">
            <div className="relative flex-1">
              <FiSearch className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input placeholder="Search customers..." className="pl-9" value={search} onChange={e => setSearch(e.target.value)} />
            </div>
            <Select value={typeFilter} onValueChange={setTypeFilter}>
              <SelectTrigger className="w-full sm:w-48">
                <SelectValue placeholder="All Types" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="">All Types</SelectItem>
                {CUSTOMER_TYPE_OPTIONS.map(o => <SelectItem key={o.value} value={o.value}>{o.label}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>

          {loading ? (
            <div className="flex justify-center py-12"><FiLoader className="animate-spin h-6 w-6 text-muted-foreground" /></div>
          ) : customers.length === 0 ? (
            <div className="text-center py-12 text-muted-foreground">No customers found</div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Customer</TableHead>
                  <TableHead>Contact</TableHead>
                  <TableHead>Address</TableHead>
                  <TableHead>Type</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {customers.map(c => {
                  const mapUrl = getMapUrl(c);
                  const wp = (c.whatsapp_number || c.phone_number || '').replace(/\D/g, '');
                  return (
                    <TableRow key={c.id}>
                      <TableCell>
                        <div className="flex items-center gap-3">
                          <Avatar className="h-8 w-8">
                            <AvatarImage src={`https://ui-avatars.com/api/?name=${encodeURIComponent(c.full_name)}&background=random&size=32`} />
                            <AvatarFallback>{c.full_name?.substring(0, 2) || 'CU'}</AvatarFallback>
                          </Avatar>
                          <div>
                            <div className="font-medium">{c.full_name}</div>
                            <div className="text-xs text-muted-foreground">{c.email || ''}</div>
                          </div>
                        </div>
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-2">
                          <span className="text-sm">{c.phone_number}</span>
                          <div className="flex items-center gap-1">
                            <a href={`tel:${c.phone_number}`} className="text-green-600 hover:text-green-800" title="Call">
                              <FiPhone className="h-4 w-4" />
                            </a>
                            {wp && (
                              <a href={`https://wa.me/${wp}`} target="_blank" rel="noopener noreferrer" className="text-green-500 hover:text-green-700" title="WhatsApp">
                                <BsWhatsapp className="h-4 w-4" />
                              </a>
                            )}
                            {mapUrl && (
                              <a href={mapUrl} target="_blank" rel="noopener noreferrer" className="text-orange-500 hover:text-orange-700" title="View on Map">
                                <FiMapPin className="h-4 w-4" />
                              </a>
                            )}
                          </div>
                        </div>
                      </TableCell>
                      <TableCell className="text-sm">
                        {[c.address_line1, c.city, c.province].filter(Boolean).join(', ') || '—'}
                      </TableCell>
                      <TableCell>
                        <span className="capitalize text-xs">{c.customer_type}</span>
                      </TableCell>
                      <TableCell>
                        <span className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium ${c.is_active ? 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300' : 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300'}`}>
                          {c.is_active ? 'Active' : 'Inactive'}
                        </span>
                      </TableCell>
                      <TableCell className="text-right">
                        <div className="flex items-center justify-end gap-1">
                          <Button variant="ghost" size="icon" onClick={() => openEdit(c)}>
                            <FiEdit2 className="h-4 w-4" />
                          </Button>
                          <Button variant="ghost" size="icon" onClick={() => setDeleteTarget(c)} className="text-red-500 hover:text-red-700">
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

      <CustomerFormDialog
        customer={formCustomer}
        open={formOpen}
        onClose={() => setFormOpen(false)}
        onSaved={fetchCustomers}
      />
      <DeleteConfirmDialog
        open={!!deleteTarget}
        onClose={() => setDeleteTarget(null)}
        onConfirm={handleDelete}
        customerName={deleteTarget?.full_name}
      />
    </div>
  );
}

