import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Separator } from "@/components/ui/separator";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter, DialogClose, DialogTrigger
} from "@/components/ui/dialog";
import { toast } from 'sonner';
import { useForm, Controller } from 'react-hook-form';
import {
  FiUser, FiUsers, FiMessageSquare, FiSearch, FiLoader, FiAlertCircle, FiEdit,
  FiPhone, FiCalendar, FiSmartphone, FiInfo
} from 'react-icons/fi';
import { formatDistanceToNow, parseISO, format, isValid as isValidDate } from 'date-fns';
import { contactsApi } from '@/lib/api';

const ProfileFieldDisplay = ({ label, value, icon, children, isDate = false }) => {
  let displayValue = value;
  if (isDate && value) {
    try {
      const dateObj = parseISO(value);
      if (isValidDate(dateObj)) displayValue = format(dateObj, 'PPP');
      else displayValue = value;
    } catch { displayValue = value; }
  }
  if (!value && !children && value !== false && value !== 0) return null;
  return (
    <div className="py-2.5 sm:grid sm:grid-cols-3 sm:gap-4 border-b dark:border-slate-700 last:border-b-0">
      <dt className="text-sm font-medium text-slate-500 dark:text-slate-400 flex items-center">
        {icon && React.cloneElement(icon, { className: "mr-2 h-4 w-4 opacity-80" })}
        {label}
      </dt>
      <dd className="mt-1 text-sm text-slate-900 dark:text-slate-50 sm:mt-0 sm:col-span-2">
        {children ? children :
          (displayValue === null || displayValue === '' ? <span className="italic text-slate-400 dark:text-slate-500">Not set</span> : String(displayValue))
        }
      </dd>
    </div>
  );
};

export default function ContactsPage() {
  const [contacts, setContacts] = useState([]);
  const [selectedContactDetails, setSelectedContactDetails] = useState(null);
  const [isLoadingContacts, setIsLoadingContacts] = useState(true);
  const [isLoadingDetails, setIsLoadingDetails] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [pagination, setPagination] = useState({ count: 0, next: null, previous: null, currentPage: 1 });

  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  const { register, handleSubmit, reset, control, formState: { isSubmitting } } = useForm({
    defaultValues: { contact_name: '', is_blocked: false, needs_human_intervention: false }
  });

  const fetchContacts = useCallback(async (page = 1, currentSearchTerm = '') => {
    setIsLoadingContacts(true);
    try {
      const filterParam = searchParams.get('filter');
      const queryParams = { page: page.toString() };
      if (currentSearchTerm) queryParams.search = currentSearchTerm;
      if (filterParam === 'needs_intervention') queryParams.needs_human_intervention = 'true';

      const response = await contactsApi.list(queryParams);
      const data = response.data;
      setContacts(data.results || data || []);
      setPagination({ count: data.count || 0, next: data.next, previous: data.previous, currentPage: page });
    } catch {
      toast.error("Couldn't load contacts");
    } finally {
      setIsLoadingContacts(false);
    }
  }, [searchParams]);

  useEffect(() => {
    fetchContacts(1, searchTerm);
  }, [fetchContacts, searchTerm]);

  const handleSelectContact = useCallback(async (contact) => {
    setIsLoadingDetails(true);
    setSelectedContactDetails(null);
    try {
      const response = await contactsApi.retrieve(contact.id);
      const detailedData = response.data;
      setSelectedContactDetails(detailedData);
      reset({
        contact_name: detailedData.name || '',
        is_blocked: detailedData.is_blocked || false,
        needs_human_intervention: detailedData.needs_human_intervention || false,
      });
    } catch {
      toast.error("Couldn't load contact details");
    } finally {
      setIsLoadingDetails(false);
    }
  }, [reset]);

  const onFormSubmit = async (formData) => {
    if (!selectedContactDetails?.id) return;
    const contactId = selectedContactDetails.id;
    const payload = {
      name: formData.contact_name,
      is_blocked: formData.is_blocked,
      needs_human_intervention: formData.needs_human_intervention,
    };
    try {
      await contactsApi.patch(contactId, payload);
      toast.success("Contact updated successfully!");
      setIsEditModalOpen(false);
      handleSelectContact({ id: contactId });
      setContacts(prev => prev.map(c => c.id === contactId ? { ...c, name: formData.contact_name, is_blocked: formData.is_blocked, needs_human_intervention: formData.needs_human_intervention } : c));
    } catch {
      toast.error("Failed to update contact");
    }
  };

  const handlePageChange = (newPage) => {
    if (newPage >= 1 && newPage <= Math.ceil(pagination.count / 20)) {
      fetchContacts(newPage, searchTerm);
    }
  };

  return (
    <div className="flex flex-1 min-h-0 border dark:border-slate-700 rounded-lg shadow-md overflow-hidden">
      {/* Contacts List Panel */}
      <div className="w-full sm:w-2/5 md:w-1/3 min-w-[300px] max-w-[450px] border-r dark:border-slate-700 flex flex-col bg-slate-50 dark:bg-slate-800/50">
        <div className="p-3 border-b dark:border-slate-700">
          <div className="relative">
            <FiSearch className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
            <Input type="search" placeholder="Search contacts..." className="pl-9 dark:bg-slate-700 dark:border-slate-600" value={searchTerm} onChange={(e) => setSearchTerm(e.target.value)} />
          </div>
        </div>
        <ScrollArea className="flex-1">
          {isLoadingContacts && contacts.length === 0 && (
            <div className="p-4 text-center">
              <FiLoader className="animate-spin h-6 w-6 mx-auto my-3 text-slate-500" />
              <p className="text-xs text-slate-400">Loading contacts...</p>
            </div>
          )}
          {!isLoadingContacts && contacts.length === 0 && (
            <div className="p-4 text-center text-sm text-slate-500 dark:text-slate-400">
              {searchTerm ? 'No contacts match your search.' : 'No contacts found. Contacts appear once messages are received.'}
            </div>
          )}
          {contacts.map(contact => (
            <div key={contact.id} onClick={() => handleSelectContact(contact)}
              className={`p-3 border-b dark:border-slate-700 cursor-pointer hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors ${selectedContactDetails?.id === contact.id ? 'bg-green-100 dark:bg-green-900/50 border-l-4 border-green-500 dark:border-green-400' : 'border-l-4 border-transparent'}`}>
              <div className="flex items-center space-x-3">
                <Avatar className="h-9 w-9">
                  <AvatarImage src={`https://ui-avatars.com/api/?name=${encodeURIComponent(contact.name || contact.whatsapp_id)}&background=random&size=96`} />
                  <AvatarFallback>{(contact.name || contact.whatsapp_id || 'U').substring(0, 1).toUpperCase()}</AvatarFallback>
                </Avatar>
                <div className="flex-1 min-w-0">
                  <p className="font-medium truncate dark:text-slate-100 text-sm">{contact.name || contact.whatsapp_id}</p>
                  <p className="text-xs text-slate-500 dark:text-slate-400 truncate">
                    {contact.whatsapp_id}
                    {contact.last_seen && ` · Seen ${formatDistanceToNow(parseISO(contact.last_seen), { addSuffix: true })}`}
                  </p>
                </div>
                {contact.needs_human_intervention && <FiAlertCircle title="Needs Human Intervention" className="h-5 w-5 text-red-500 flex-shrink-0" />}
              </div>
            </div>
          ))}
        </ScrollArea>
        {pagination.count > 0 && (
          <div className="p-2 border-t dark:border-slate-700 flex justify-between items-center text-xs">
            <Button variant="outline" size="sm" onClick={() => handlePageChange(pagination.currentPage - 1)} disabled={!pagination.previous || isLoadingContacts}>Prev</Button>
            <span>Page {pagination.currentPage} of {Math.max(1, Math.ceil(pagination.count / 20))}</span>
            <Button variant="outline" size="sm" onClick={() => handlePageChange(pagination.currentPage + 1)} disabled={!pagination.next || isLoadingContacts}>Next</Button>
          </div>
        )}
      </div>

      {/* Contact Details Panel */}
      <ScrollArea className="flex-1 bg-white dark:bg-slate-900">
        {isLoadingDetails && <div className="flex items-center justify-center h-full p-10"><FiLoader className="animate-spin h-10 w-10 text-green-500" /></div>}
        {!isLoadingDetails && selectedContactDetails ? (
          <div className="p-4 sm:p-6 space-y-6">
            <Card className="dark:bg-slate-800 dark:border-slate-700">
              <CardHeader className="flex flex-col sm:flex-row justify-between sm:items-start gap-2 pb-4">
                <div className="flex items-center gap-4">
                  <Avatar className="h-16 w-16 border-2 dark:border-slate-600">
                    <AvatarImage src={`https://ui-avatars.com/api/?name=${encodeURIComponent(selectedContactDetails.name || selectedContactDetails.whatsapp_id)}&background=random&size=128`} />
                    <AvatarFallback className="text-2xl">{(selectedContactDetails.name || selectedContactDetails.whatsapp_id || 'U').substring(0, 2).toUpperCase()}</AvatarFallback>
                  </Avatar>
                  <div>
                    <CardTitle className="text-xl md:text-2xl dark:text-slate-50">{selectedContactDetails.name || selectedContactDetails.whatsapp_id}</CardTitle>
                    <CardDescription className="dark:text-slate-400 mt-1">{selectedContactDetails.whatsapp_id}</CardDescription>
                    <div className="mt-2 flex flex-wrap gap-2">
                      {selectedContactDetails.is_blocked && <Badge variant="destructive">Blocked</Badge>}
                      {selectedContactDetails.needs_human_intervention && <Badge className="bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300">Needs Intervention</Badge>}
                    </div>
                  </div>
                </div>
                <div className="flex flex-col sm:flex-row gap-2 sm:items-center pt-2 sm:pt-0 w-full sm:w-auto">
                  <Button variant="outline" size="sm" onClick={() => navigate(`/conversation?contactId=${selectedContactDetails.id}`)} className="dark:text-slate-300 dark:border-slate-600 w-full sm:w-auto">
                    <FiMessageSquare className="mr-2 h-4 w-4" /> View Chat
                  </Button>
                  <Dialog open={isEditModalOpen} onOpenChange={setIsEditModalOpen}>
                    <DialogTrigger asChild>
                      <Button size="sm" className="bg-green-600 hover:bg-green-700 dark:bg-green-500 dark:hover:bg-green-600 text-white w-full sm:w-auto">
                        <FiEdit className="mr-2 h-4 w-4" /> Edit Contact
                      </Button>
                    </DialogTrigger>
                    <DialogContent className="sm:max-w-lg dark:bg-slate-800 dark:text-slate-50">
                      <DialogHeader>
                        <DialogTitle>Edit Contact: {selectedContactDetails.name || selectedContactDetails.whatsapp_id}</DialogTitle>
                        <DialogDescription>Update contact details.</DialogDescription>
                      </DialogHeader>
                      <form onSubmit={handleSubmit(onFormSubmit)} className="space-y-4 mt-2">
                        <div>
                          <Label htmlFor="contact_name">Display Name</Label>
                          <Input id="contact_name" {...register("contact_name")} className="dark:bg-slate-700 dark:border-slate-600" />
                        </div>
                        <div className="flex items-center space-x-2">
                          <Controller name="is_blocked" control={control} render={({ field }) => <Switch id="is_blocked" checked={field.value} onCheckedChange={field.onChange} />} />
                          <Label htmlFor="is_blocked" className="cursor-pointer">Is Blocked</Label>
                        </div>
                        <div className="flex items-center space-x-2">
                          <Controller name="needs_human_intervention" control={control} render={({ field }) => <Switch id="needs_human_intervention" checked={field.value} onCheckedChange={field.onChange} />} />
                          <Label htmlFor="needs_human_intervention" className="cursor-pointer">Needs Human Intervention</Label>
                        </div>
                        <DialogFooter className="pt-4">
                          <DialogClose asChild><Button type="button" variant="outline" className="dark:text-slate-300 dark:border-slate-600">Cancel</Button></DialogClose>
                          <Button type="submit" disabled={isSubmitting} className="bg-green-600 hover:bg-green-700 text-white">
                            {isSubmitting ? <FiLoader className="animate-spin" /> : "Save Changes"}
                          </Button>
                        </DialogFooter>
                      </form>
                    </DialogContent>
                  </Dialog>
                </div>
              </CardHeader>
              <CardContent className="pt-4">
                <dl className="divide-y dark:divide-slate-700">
                  <ProfileFieldDisplay label="Display Name" value={selectedContactDetails.display_name || selectedContactDetails.name} icon={<FiUser />} />
                  <ProfileFieldDisplay label="WhatsApp ID" value={selectedContactDetails.whatsapp_id} icon={<FiSmartphone />} />
                  <ProfileFieldDisplay label="Phone Number" value={selectedContactDetails.phone_number} icon={<FiPhone />} />
                  <ProfileFieldDisplay label="Profile Name" value={selectedContactDetails.profile_name} icon={<FiUser />} />
                  <ProfileFieldDisplay label="Messages" value={selectedContactDetails.message_count} icon={<FiMessageSquare />} />
                  <ProfileFieldDisplay label="Unread" value={selectedContactDetails.unread_count} icon={<FiInfo />} />
                  <ProfileFieldDisplay label="Last Message" value={selectedContactDetails.last_message_preview} icon={<FiMessageSquare />} />
                  <ProfileFieldDisplay label="First Seen" value={selectedContactDetails.created_at} isDate icon={<FiCalendar />} />
                  <ProfileFieldDisplay label="Last Interaction" value={selectedContactDetails.last_seen} isDate icon={<FiCalendar />} />
                </dl>
              </CardContent>
            </Card>
          </div>
        ) : searchTerm && !isLoadingContacts && contacts.length === 0 ? (
          <div className="flex-1 flex flex-col items-center justify-center text-slate-500 dark:text-slate-400 p-10 text-center">
            <FiSearch className="h-24 w-24 mb-6 text-slate-300 dark:text-slate-600" />
            <p className="text-lg font-medium">No results for &quot;{searchTerm}&quot;</p>
            <p className="text-sm">Try searching for something else.</p>
          </div>
        ) : (
          <div className="flex-1 flex flex-col items-center justify-center text-slate-500 dark:text-slate-400 p-10 text-center">
            <FiUsers className="h-24 w-24 mb-6 text-slate-300 dark:text-slate-600" />
            <p className="text-lg font-medium">Select a contact to view their details.</p>
            <p className="text-sm">Or use the search to find a specific contact.</p>
          </div>
        )}
      </ScrollArea>
    </div>
  );
}

