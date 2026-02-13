import React from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { FiUsers } from 'react-icons/fi';

export default function ContactsPage() {
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Contacts</h1>
      <Card className="dark:bg-slate-800"><CardHeader><CardTitle className="flex items-center"><FiUsers className="mr-2" /> Contact Management</CardTitle></CardHeader>
        <CardContent><p className="text-muted-foreground">Contact management will be available once the backend API is connected. View and manage all WhatsApp contacts from here.</p></CardContent>
      </Card>
    </div>
  );
}
