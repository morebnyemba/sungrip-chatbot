import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { toast } from 'sonner';
import { FiImage, FiLoader, FiUploadCloud, FiRefreshCw, FiTrash2, FiSearch, FiX } from 'react-icons/fi';
import { API_BASE_URL } from '@/lib/api';
import apiClient from '@/lib/api';

export default function MediaLibraryPage() {
  const [files, setFiles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [search, setSearch] = useState('');
  const [preview, setPreview] = useState(null);
  const fileInputRef = useRef(null);

  const fetchMedia = useCallback(async () => {
    setLoading(true);
    try {
      const res = await apiClient.get('/api/products/', { params: { page_size: 100 } });
      const products = res.data.results || res.data || [];
      const mediaItems = products
        .filter(p => p.image || p.image_url)
        .map(p => ({
          id: p.id,
          name: p.name,
          url: p.image || p.image_url,
          type: 'product_image',
          product_type: p.product_type,
        }));
      setFiles(mediaItems);
    } catch {
      toast.error('Failed to load media');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchMedia(); }, [fetchMedia]);

  const filteredFiles = files.filter(f =>
    !search || f.name.toLowerCase().includes(search.toLowerCase())
  );

  const handleUploadClick = () => {
    toast.info('Direct media upload will be available in a future update. For now, add images through the Products page.');
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Media Library</h1>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={fetchMedia}><FiRefreshCw className="mr-2 h-4 w-4" />Refresh</Button>
          <Button size="sm" onClick={handleUploadClick}><FiUploadCloud className="mr-2 h-4 w-4" />Upload</Button>
        </div>
      </div>

      <div className="relative max-w-sm">
        <FiSearch className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
        <Input placeholder="Search media..." className="pl-9" value={search} onChange={e => setSearch(e.target.value)} />
      </div>

      {loading ? (
        <div className="flex justify-center py-20"><FiLoader className="animate-spin h-8 w-8 text-muted-foreground" /></div>
      ) : filteredFiles.length === 0 ? (
        <Card className="dark:bg-slate-800">
          <CardContent className="py-12 text-center text-muted-foreground">
            <FiImage className="h-12 w-12 mx-auto mb-4 opacity-30" />
            <p className="text-lg font-medium">{search ? 'No media matches your search' : 'No media files found'}</p>
            <p className="text-sm mt-1">Product images will appear here once products are added.</p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
          {filteredFiles.map(file => (
            <Card key={file.id} className="dark:bg-slate-800 overflow-hidden cursor-pointer hover:ring-2 hover:ring-primary transition-all" onClick={() => setPreview(file)}>
              <div className="aspect-square bg-muted flex items-center justify-center overflow-hidden">
                {file.url ? (
                  <img
                    src={file.url.startsWith('http') ? file.url : `${API_BASE_URL}${file.url}`}
                    alt={file.name}
                    className="object-cover w-full h-full"
                    onError={(e) => { e.target.style.display = 'none'; }}
                  />
                ) : (
                  <FiImage className="h-8 w-8 text-muted-foreground/30" />
                )}
              </div>
              <CardContent className="p-2">
                <p className="text-xs font-medium truncate">{file.name}</p>
                <p className="text-xs text-muted-foreground capitalize">{file.product_type?.replace(/_/g, ' ')}</p>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {preview && (
        <div className="fixed inset-0 z-50 bg-black/80 flex items-center justify-center p-4" onClick={() => setPreview(null)}>
          <div className="relative max-w-2xl max-h-[80vh]" onClick={e => e.stopPropagation()}>
            <Button variant="ghost" size="icon" className="absolute -top-10 right-0 text-white" onClick={() => setPreview(null)}><FiX className="h-5 w-5" /></Button>
            {preview.url && (
              <img
                src={preview.url.startsWith('http') ? preview.url : `${API_BASE_URL}${preview.url}`}
                alt={preview.name}
                className="max-w-full max-h-[70vh] object-contain rounded-lg"
              />
            )}
            <p className="text-white text-center mt-2 text-sm">{preview.name}</p>
          </div>
        </div>
      )}
    </div>
  );
}
