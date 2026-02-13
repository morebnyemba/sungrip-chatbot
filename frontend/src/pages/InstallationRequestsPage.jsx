import React from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { FiActivity } from 'react-icons/fi';

export default function InstallationRequestsPage() {
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Installation Requests</h1>
      <Card className="dark:bg-slate-800"><CardHeader><CardTitle className="flex items-center"><FiActivity className="mr-2" /> Installation Request Management</CardTitle></CardHeader>
        <CardContent><p className="text-muted-foreground">Track and manage solar installation requests from customers.</p></CardContent>
      </Card>
    </div>
  );
}
