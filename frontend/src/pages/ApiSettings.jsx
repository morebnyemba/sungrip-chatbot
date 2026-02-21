import React, { useState, useEffect, useCallback } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { Badge } from '@/components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { toast } from 'sonner';
import { FiSettings, FiLoader, FiEdit2, FiPlus, FiTrash2, FiRefreshCw, FiCheck, FiX } from 'react-icons/fi';
import { metaConfigsApi } from '@/lib/api';

const EMPTY_CONFIG = { name: '', phone_number_id: '', waba_id: '', access_token: '', app_secret: '', verify_token: '', catalog_id: '', api_version: 'v19.0', is_active: false };

export default function ApiSettings() {
  const [configs, setConfigs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [editConfig, setEditConfig] = useState(null);
  const [form, setForm] = useState(EMPTY_CONFIG);
  const [saving, setSaving] = useState(false);

  const fetchConfigs = useCallback(async () => {
    setLoading(true);
    try {
      const res = await metaConfigsApi.list();
      setConfigs(res.data.results || res.data || []);
    } catch {
      toast.error('Failed to load API configurations');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchConfigs(); }, [fetchConfigs]);

  const openEdit = (config = null) => {
    if (config) {
      setForm({ ...EMPTY_CONFIG, ...config });
      setEditConfig(config);
    } else {
      setForm({ ...EMPTY_CONFIG });
      setEditConfig('new');
    }
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      if (editConfig === 'new') {
        await metaConfigsApi.create(form);
        toast.success('Configuration created');
      } else {
        await metaConfigsApi.update(editConfig.id, form);
        toast.success('Configuration updated');
      }
      setEditConfig(null);
      fetchConfigs();
    } catch {
      toast.error('Failed to save configuration');
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Delete this configuration?')) return;
    try {
      await metaConfigsApi.delete(id);
      toast.success('Configuration deleted');
      fetchConfigs();
    } catch {
      toast.error('Failed to delete configuration');
    }
  };

  const updateField = (field, value) => setForm(prev => ({ ...prev, [field]: value }));

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">API Settings</h1>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={fetchConfigs}><FiRefreshCw className="mr-2 h-4 w-4" />Refresh</Button>
          <Button size="sm" onClick={() => openEdit()}><FiPlus className="mr-2 h-4 w-4" />Add Config</Button>
        </div>
      </div>

      {loading ? (
        <div className="flex justify-center py-12"><FiLoader className="animate-spin h-6 w-6 text-muted-foreground" /></div>
      ) : configs.length === 0 ? (
        <Card className="dark:bg-slate-800">
          <CardContent className="py-12 text-center text-muted-foreground">
            <FiSettings className="h-12 w-12 mx-auto mb-4 opacity-30" />
            <p className="text-lg font-medium">No API configurations found</p>
            <p className="text-sm mt-1">Add your Meta WhatsApp Business API credentials to get started.</p>
            <Button className="mt-4" onClick={() => openEdit()}><FiPlus className="mr-2 h-4 w-4" />Add Configuration</Button>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4">
          {configs.map(config => (
            <Card key={config.id} className="dark:bg-slate-800">
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <div className="flex items-center gap-3">
                  <CardTitle className="text-lg">{config.name}</CardTitle>
                  {config.is_active ? <Badge className="bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300"><FiCheck className="mr-1 h-3 w-3" />Active</Badge>
                    : <Badge variant="secondary"><FiX className="mr-1 h-3 w-3" />Inactive</Badge>}
                </div>
                <div className="flex gap-1">
                  <Button variant="ghost" size="icon" onClick={() => openEdit(config)}><FiEdit2 className="h-4 w-4" /></Button>
                  <Button variant="ghost" size="icon" className="text-red-500" onClick={() => handleDelete(config.id)}><FiTrash2 className="h-4 w-4" /></Button>
                </div>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 md:grid-cols-3 gap-3 text-sm">
                  <div><span className="text-muted-foreground">Phone Number ID:</span> <span className="font-mono">{config.phone_number_id}</span></div>
                  <div><span className="text-muted-foreground">WABA ID:</span> <span className="font-mono">{config.waba_id}</span></div>
                  <div><span className="text-muted-foreground">API Version:</span> <span>{config.api_version}</span></div>
                  {config.catalog_id && <div><span className="text-muted-foreground">Catalog ID:</span> <span className="font-mono">{config.catalog_id}</span></div>}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      <Dialog open={!!editConfig} onOpenChange={() => setEditConfig(null)}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>{editConfig === 'new' ? 'Add API Configuration' : 'Edit API Configuration'}</DialogTitle>
          </DialogHeader>
          <div className="space-y-3">
            <div><Label>Name</Label><Input value={form.name} onChange={e => updateField('name', e.target.value)} placeholder="e.g. Primary Business Account" /></div>
            <div><Label>Phone Number ID</Label><Input value={form.phone_number_id} onChange={e => updateField('phone_number_id', e.target.value)} /></div>
            <div><Label>WABA ID</Label><Input value={form.waba_id} onChange={e => updateField('waba_id', e.target.value)} /></div>
            <div><Label>Access Token</Label><Input type="password" value={form.access_token} onChange={e => updateField('access_token', e.target.value)} /></div>
            <div><Label>App Secret</Label><Input type="password" value={form.app_secret || ''} onChange={e => updateField('app_secret', e.target.value)} /></div>
            <div><Label>Verify Token</Label><Input value={form.verify_token} onChange={e => updateField('verify_token', e.target.value)} /></div>
            <div className="grid grid-cols-2 gap-3">
              <div><Label>Catalog ID</Label><Input value={form.catalog_id || ''} onChange={e => updateField('catalog_id', e.target.value)} /></div>
              <div><Label>API Version</Label><Input value={form.api_version} onChange={e => updateField('api_version', e.target.value)} /></div>
            </div>
            <div className="flex items-center gap-2">
              <Switch checked={form.is_active} onCheckedChange={v => updateField('is_active', v)} />
              <Label>Active</Label>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setEditConfig(null)}>Cancel</Button>
            <Button onClick={handleSave} disabled={saving}>{saving && <FiLoader className="animate-spin mr-2 h-4 w-4" />}Save</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
