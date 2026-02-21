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
import { FiSearch, FiLoader, FiEdit2, FiTrash2, FiRefreshCw, FiAlertCircle } from 'react-icons/fi';
import { productsApi } from '@/lib/api';
import { useDebounce } from 'use-debounce';

const PRODUCT_TYPES = [
  { value: 'solar_panel', label: 'Solar Panel' },
  { value: 'inverter', label: 'Inverter' },
  { value: 'battery', label: 'Battery' },
  { value: 'charge_controller', label: 'Charge Controller' },
  { value: 'mounting', label: 'Mounting Equipment' },
  { value: 'cable', label: 'Cables & Wiring' },
  { value: 'accessory', label: 'Accessory' },
  { value: 'service', label: 'Service/Labor' },
];

const emptyForm = {
  name: '', brand: '', model_number: '', sku: '', product_type: 'solar_panel',
  short_description: '', selling_price: '', cost_price: '', currency: 'USD',
  stock_quantity: 0, warranty_period_months: 12, is_active: true, is_featured: false,
};

function ProductFormDialog({ product, open, onClose, onSaved }) {
  const isEdit = !!product?.id;
  const [form, setForm] = useState(emptyForm);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (product) {
      setForm({
        name: product.name || '',
        brand: product.brand || '',
        model_number: product.model_number || '',
        sku: product.sku || '',
        product_type: product.product_type || 'solar_panel',
        short_description: product.short_description || '',
        selling_price: product.selling_price || '',
        cost_price: product.cost_price || '',
        currency: product.currency || 'USD',
        stock_quantity: product.stock_quantity ?? 0,
        warranty_period_months: product.warranty_period_months || 12,
        is_active: product.is_active ?? true,
        is_featured: product.is_featured ?? false,
      });
    } else {
      setForm(emptyForm);
    }
  }, [product]);

  const set = (field) => (e) => setForm(prev => ({ ...prev, [field]: e.target?.value ?? e }));

  const handleSave = async () => {
    if (!form.name || !form.sku) {
      toast.error('Product name and SKU are required');
      return;
    }
    setSaving(true);
    try {
      if (isEdit) {
        await productsApi.update(product.id, form);
        toast.success('Product updated');
      } else {
        await productsApi.create(form);
        toast.success('Product created');
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
          <DialogTitle>{isEdit ? 'Edit Product' : 'New Product'}</DialogTitle>
        </DialogHeader>
        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-1 col-span-2 sm:col-span-1">
            <Label>Name *</Label>
            <Input value={form.name} onChange={set('name')} placeholder="Product Name" />
          </div>
          <div className="space-y-1 col-span-2 sm:col-span-1">
            <Label>SKU *</Label>
            <Input value={form.sku} onChange={set('sku')} placeholder="SKU-001" />
          </div>
          <div className="space-y-1">
            <Label>Brand</Label>
            <Input value={form.brand} onChange={set('brand')} placeholder="Brand" />
          </div>
          <div className="space-y-1">
            <Label>Model Number</Label>
            <Input value={form.model_number} onChange={set('model_number')} placeholder="Model Number" />
          </div>
          <div className="space-y-1">
            <Label>Product Type</Label>
            <Select value={form.product_type} onValueChange={set('product_type')}>
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>
                {PRODUCT_TYPES.map(t => <SelectItem key={t.value} value={t.value}>{t.label}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-1">
            <Label>Currency</Label>
            <Input value={form.currency} onChange={set('currency')} placeholder="USD" maxLength={3} />
          </div>
          <div className="space-y-1">
            <Label>Selling Price</Label>
            <Input type="number" value={form.selling_price} onChange={set('selling_price')} placeholder="0.00" min="0" step="0.01" />
          </div>
          <div className="space-y-1">
            <Label>Cost Price</Label>
            <Input type="number" value={form.cost_price} onChange={set('cost_price')} placeholder="0.00" min="0" step="0.01" />
          </div>
          <div className="space-y-1">
            <Label>Stock Quantity</Label>
            <Input type="number" value={form.stock_quantity} onChange={set('stock_quantity')} min="0" />
          </div>
          <div className="space-y-1">
            <Label>Warranty (months)</Label>
            <Input type="number" value={form.warranty_period_months} onChange={set('warranty_period_months')} min="0" />
          </div>
          <div className="space-y-1 col-span-2">
            <Label>Short Description</Label>
            <Textarea value={form.short_description} onChange={set('short_description')} rows={2} placeholder="Brief product description..." />
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
          <div className="space-y-1">
            <Label>Featured</Label>
            <Select value={form.is_featured ? 'yes' : 'no'} onValueChange={v => setForm(prev => ({ ...prev, is_featured: v === 'yes' }))}>
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="yes">Featured</SelectItem>
                <SelectItem value="no">Not Featured</SelectItem>
              </SelectContent>
            </Select>
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

function DeleteConfirmDialog({ open, onClose, onConfirm, productName }) {
  const [deleting, setDeleting] = useState(false);
  const handleConfirm = async () => { setDeleting(true); await onConfirm(); setDeleting(false); };
  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent>
        <DialogHeader><DialogTitle>Delete Product</DialogTitle></DialogHeader>
        <p className="text-sm text-muted-foreground">Delete <strong>{productName}</strong>? This cannot be undone.</p>
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

export default function ProductsPage() {
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [debouncedSearch] = useDebounce(search, 300);
  const [typeFilter, setTypeFilter] = useState('');
  const [formProduct, setFormProduct] = useState(null);
  const [formOpen, setFormOpen] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState(null);

  const fetchProducts = useCallback(async () => {
    setLoading(true);
    try {
      const params = {};
      if (debouncedSearch) params.search = debouncedSearch;
      if (typeFilter) params.product_type = typeFilter;
      const res = await productsApi.list(params);
      setProducts(res.data.results || res.data || []);
    } catch {
      toast.error("Failed to load products");
    } finally {
      setLoading(false);
    }
  }, [debouncedSearch, typeFilter]);

  useEffect(() => { fetchProducts(); }, [fetchProducts]);

  const openCreate = () => { setFormProduct(null); setFormOpen(true); };
  const openEdit = (p) => { setFormProduct(p); setFormOpen(true); };

  const handleDelete = async () => {
    try {
      await productsApi.delete(deleteTarget.id);
      toast.success('Product deleted');
      setDeleteTarget(null);
      fetchProducts();
    } catch {
      toast.error('Failed to delete product');
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Products</h1>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={fetchProducts}>
            <FiRefreshCw className="mr-2 h-4 w-4" />Refresh
          </Button>
          <Button size="sm" onClick={openCreate}>+ New Product</Button>
        </div>
      </div>

      <Card className="dark:bg-slate-800">
        <CardContent className="p-4">
          <div className="flex flex-col sm:flex-row gap-3 mb-4">
            <div className="relative flex-1">
              <FiSearch className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input placeholder="Search products..." className="pl-9" value={search} onChange={e => setSearch(e.target.value)} />
            </div>
            <Select value={typeFilter} onValueChange={setTypeFilter}>
              <SelectTrigger className="w-full sm:w-48">
                <SelectValue placeholder="All Types" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="">All Types</SelectItem>
                {PRODUCT_TYPES.map(t => <SelectItem key={t.value} value={t.value}>{t.label}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>

          {loading ? (
            <div className="flex justify-center py-12"><FiLoader className="animate-spin h-6 w-6 text-muted-foreground" /></div>
          ) : products.length === 0 ? (
            <div className="text-center py-12 text-muted-foreground">No products found</div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Product</TableHead>
                  <TableHead>SKU</TableHead>
                  <TableHead>Type</TableHead>
                  <TableHead>Price</TableHead>
                  <TableHead>Stock</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {products.map(p => (
                  <TableRow key={p.id}>
                    <TableCell>
                      <div className="font-medium">{p.name}</div>
                      <div className="text-xs text-muted-foreground">{p.brand}</div>
                    </TableCell>
                    <TableCell className="font-mono text-xs">{p.sku}</TableCell>
                    <TableCell>
                      <span className="text-xs capitalize">{p.product_type?.replace(/_/g, ' ')}</span>
                    </TableCell>
                    <TableCell>{p.currency} {Number(p.selling_price).toFixed(2)}</TableCell>
                    <TableCell>
                      <div className="flex items-center gap-1">
                        {p.is_low_stock && <FiAlertCircle className="h-3.5 w-3.5 text-orange-500" title="Low stock" />}
                        {p.stock_quantity}
                      </div>
                    </TableCell>
                    <TableCell>
                      <span className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium ${p.is_active ? 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300' : 'bg-red-100 text-red-800'}`}>
                        {p.is_active ? 'Active' : 'Inactive'}
                      </span>
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex items-center justify-end gap-1">
                        <Button variant="ghost" size="icon" onClick={() => openEdit(p)}>
                          <FiEdit2 className="h-4 w-4" />
                        </Button>
                        <Button variant="ghost" size="icon" onClick={() => setDeleteTarget(p)} className="text-red-500 hover:text-red-700">
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

      <ProductFormDialog product={formProduct} open={formOpen} onClose={() => setFormOpen(false)} onSaved={fetchProducts} />
      <DeleteConfirmDialog open={!!deleteTarget} onClose={() => setDeleteTarget(null)} onConfirm={handleDelete} productName={deleteTarget?.name} />
    </div>
  );
}
