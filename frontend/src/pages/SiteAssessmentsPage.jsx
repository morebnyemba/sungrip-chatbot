import React, { useState, useEffect, useCallback } from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { toast } from 'sonner';
import { FiSearch, FiLoader, FiEye, FiRefreshCw, FiMapPin } from 'react-icons/fi';
import { formatDistanceToNow, parseISO } from 'date-fns';
import { installationsApi } from '@/lib/api';
import { useDebounce } from 'use-debounce';

const STATUS_COLORS = {
  scheduled: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300',
  in_progress: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300',
  completed: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300',
  on_hold: 'bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-300',
  cancelled: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300',
};

const STATUS_OPTIONS = [
  { value: 'all', label: 'All Statuses' },
  { value: 'scheduled', label: 'Scheduled' },
  { value: 'in_progress', label: 'In Progress' },
  { value: 'completed', label: 'Completed' },
  { value: 'on_hold', label: 'On Hold' },
  { value: 'cancelled', label: 'Cancelled' },
];

export default function SiteAssessmentsPage() {
  const [installations, setInstallations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [debouncedSearch] = useDebounce(search, 300);
  const [statusFilter, setStatusFilter] = useState('all');
  const [selected, setSelected] = useState(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const params = {};
      if (debouncedSearch) params.search = debouncedSearch;
      if (statusFilter && statusFilter !== 'all') params.status = statusFilter;
      const res = await installationsApi.list(params);
      setInstallations(res.data.results || res.data || []);
    } catch {
      toast.error('Failed to load installations');
    } finally {
      setLoading(false);
    }
  }, [debouncedSearch, statusFilter]);

  useEffect(() => { fetchData(); }, [fetchData]);

  const getMapUrl = (inst) => {
    if (inst.gps_latitude && inst.gps_longitude) {
      return `https://www.google.com/maps?q=${inst.gps_latitude},${inst.gps_longitude}`;
    }
    if (inst.installation_address) {
      return `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(inst.installation_address)}`;
    }
    return null;
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Site Assessments</h1>
        <Button variant="outline" size="sm" onClick={fetchData}><FiRefreshCw className="mr-2 h-4 w-4" />Refresh</Button>
      </div>

      <Card className="dark:bg-slate-800">
        <CardContent className="p-4">
          <div className="flex flex-col sm:flex-row gap-3 mb-4">
            <div className="relative flex-1">
              <FiSearch className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input placeholder="Search installations..." className="pl-9" value={search} onChange={e => setSearch(e.target.value)} />
            </div>
            <Select value={statusFilter} onValueChange={setStatusFilter}>
              <SelectTrigger className="w-full sm:w-48"><SelectValue placeholder="Filter by status" /></SelectTrigger>
              <SelectContent>
                {STATUS_OPTIONS.map(o => <SelectItem key={o.value} value={o.value}>{o.label}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>

          {loading ? (
            <div className="flex justify-center py-12"><FiLoader className="animate-spin h-6 w-6 text-muted-foreground" /></div>
          ) : installations.length === 0 ? (
            <div className="text-center py-12 text-muted-foreground">No installations found</div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Customer</TableHead>
                  <TableHead>System Size</TableHead>
                  <TableHead>Panels</TableHead>
                  <TableHead>Scheduled</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {installations.map(inst => (
                  <TableRow key={inst.id}>
                    <TableCell>
                      <div className="font-medium">{inst.customer_name || `Customer #${inst.customer}`}</div>
                      <div className="text-xs text-muted-foreground truncate max-w-[200px]">{inst.installation_address}</div>
                    </TableCell>
                    <TableCell>{inst.system_size_kw} kW</TableCell>
                    <TableCell>{inst.number_of_panels}</TableCell>
                    <TableCell className="text-xs">{inst.scheduled_date || '—'}</TableCell>
                    <TableCell>
                      <Badge className={STATUS_COLORS[inst.status] || ''}>
                        {inst.status?.replace(/_/g, ' ')}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-1">
                        <Button variant="ghost" size="icon" onClick={() => setSelected(inst)}><FiEye className="h-4 w-4" /></Button>
                        {getMapUrl(inst) && (
                          <Button variant="ghost" size="icon" asChild>
                            <a href={getMapUrl(inst)} target="_blank" rel="noopener noreferrer"><FiMapPin className="h-4 w-4 text-orange-500" /></a>
                          </Button>
                        )}
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      <Dialog open={!!selected} onOpenChange={() => setSelected(null)}>
        <DialogContent className="max-w-lg">
          <DialogHeader><DialogTitle>Installation Details</DialogTitle></DialogHeader>
          {selected && (
            <div className="grid grid-cols-2 gap-3 text-sm">
              <div><span className="text-muted-foreground">Address:</span> <span>{selected.installation_address}</span></div>
              <div><span className="text-muted-foreground">System Size:</span> <span>{selected.system_size_kw} kW</span></div>
              <div><span className="text-muted-foreground">Panels:</span> <span>{selected.number_of_panels}</span></div>
              {selected.inverter_model && <div><span className="text-muted-foreground">Inverter:</span> <span>{selected.inverter_model}</span></div>}
              {selected.battery_capacity_kwh && <div><span className="text-muted-foreground">Battery:</span> <span>{selected.battery_capacity_kwh} kWh</span></div>}
              <div><span className="text-muted-foreground">Scheduled:</span> <span>{selected.scheduled_date || '—'}</span></div>
              <div><span className="text-muted-foreground">Duration:</span> <span>{selected.estimated_duration_days} day(s)</span></div>
              <div><span className="text-muted-foreground">Status:</span> <Badge className={STATUS_COLORS[selected.status] || ''}>{selected.status?.replace(/_/g, ' ')}</Badge></div>
              {selected.notes && <div className="col-span-2"><span className="text-muted-foreground">Notes:</span> <span>{selected.notes}</span></div>}
              {selected.created_at && <div className="col-span-2 text-xs text-muted-foreground">Created {formatDistanceToNow(parseISO(selected.created_at), { addSuffix: true })}</div>}
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
