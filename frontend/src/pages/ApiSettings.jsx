import React from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { FiSettings } from 'react-icons/fi';

export default function ApiSettings() {
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">API Settings</h1>
      <Card className="dark:bg-slate-800"><CardHeader><CardTitle className="flex items-center"><FiSettings className="mr-2" /> WhatsApp API Configuration</CardTitle></CardHeader>
        <CardContent><p className="text-muted-foreground">Configure your Meta WhatsApp Business API credentials and webhook settings.</p></CardContent>
      </Card>
    </div>
  );
}
