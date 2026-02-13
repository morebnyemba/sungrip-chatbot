import React from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { FiBarChart2 } from 'react-icons/fi';

export default function AnalyticsPage() {
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Analytics</h1>
      <Card className="dark:bg-slate-800"><CardHeader><CardTitle className="flex items-center"><FiBarChart2 className="mr-2" /> Analytics Dashboard</CardTitle></CardHeader>
        <CardContent><p className="text-muted-foreground">View analytics and reports about conversations, customer engagement, and sales.</p></CardContent>
      </Card>
    </div>
  );
}
