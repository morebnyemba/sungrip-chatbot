import React from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { FiCreditCard } from 'react-icons/fi';

export default function OrdersPage() {
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Orders</h1>
      <Card className="dark:bg-slate-800"><CardHeader><CardTitle className="flex items-center"><FiCreditCard className="mr-2" /> Order Management</CardTitle></CardHeader>
        <CardContent><p className="text-muted-foreground">View and manage solar equipment orders placed through the WhatsApp chatbot.</p></CardContent>
      </Card>
    </div>
  );
}
