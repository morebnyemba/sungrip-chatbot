import React from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { FiImage } from 'react-icons/fi';

export default function MediaLibraryPage() {
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Media Library</h1>
      <Card className="dark:bg-slate-800"><CardHeader><CardTitle className="flex items-center"><FiImage className="mr-2" /> Media Assets</CardTitle></CardHeader>
        <CardContent><p className="text-muted-foreground">Manage media files for use in WhatsApp messages and templates.</p></CardContent>
      </Card>
    </div>
  );
}
