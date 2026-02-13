import React from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { FiBarChart2 } from 'react-icons/fi';

export default function SiteAssessmentsPage() {
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Site Assessments</h1>
      <Card className="dark:bg-slate-800"><CardHeader><CardTitle className="flex items-center"><FiBarChart2 className="mr-2" /> Site Assessment Management</CardTitle></CardHeader>
        <CardContent><p className="text-muted-foreground">Manage site assessment data collected during solar installation planning.</p></CardContent>
      </Card>
    </div>
  );
}
