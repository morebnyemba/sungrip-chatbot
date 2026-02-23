import React, { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import { useAtom } from 'jotai';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Tooltip, TooltipTrigger, TooltipContent, TooltipProvider } from "@/components/ui/tooltip";
import { toast } from 'sonner';
import {
  FiSend, FiUsers, FiMessageSquare, FiSearch, FiLoader, FiAlertCircle,
  FiPaperclip, FiArrowLeft, FiCheck, FiClock, FiMoreVertical, FiChevronRight,
  FiPhone, FiMapPin
} from 'react-icons/fi';
import { BsWhatsapp } from 'react-icons/bs';
import { formatDistanceToNow, parseISO } from 'date-fns';
import { contactsApi, API_BASE_URL } from '@/lib/api';
import { selectedContactAtom } from '@/atoms/conversationAtoms';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { useDebounce } from 'use-debounce';
import { useAuth } from '@/context/AuthContext';
import useWebSocket, { ReadyState } from 'react-use-websocket';

const MessageBubble = ({ message, isLast }) => {
  const isOutgoing = message.direction === 'out';
  const bubbleClass = isOutgoing
    ? 'bg-primary text-primary-foreground rounded-se-none'
    : 'bg-muted text-foreground rounded-ss-none';

  const statusIcons = {
    sent: <FiCheck className="h-3 w-3 text-muted-foreground" title="Sent" />,
    delivered: <div className="flex gap-0.5"><FiCheck className="h-3 w-3 text-muted-foreground" /><FiCheck className="h-3 w-3 text-muted-foreground -ml-1" /></div>,
    read: <div className="flex gap-0.5"><FiCheck className="h-3 w-3 text-blue-500" /><FiCheck className="h-3 w-3 text-blue-500 -ml-1" /></div>,
    failed: <FiAlertCircle className="h-3 w-3 text-destructive" />,
    pending: <FiClock className="h-3 w-3 text-muted-foreground animate-pulse" />
  };

  return (
    <div className={`flex flex-col my-1.5 ${isOutgoing ? 'items-end' : 'items-start'}`}>
      <div className={`max-w-[85%] sm:max-w-[75%] px-3 py-2 rounded-xl shadow-sm ${bubbleClass}`}>
        <div className="text-sm break-words whitespace-pre-wrap overflow-hidden">
          {message.text_content ? <p className="leading-relaxed">{message.text_content}</p> : <p className="italic text-muted-foreground/80">{message.content_preview || '[Unsupported message type]'}</p>}
        </div>
      </div>
      <div className={`flex items-center gap-1 mt-1 px-1 ${isOutgoing ? 'flex-row-reverse' : ''}`}>
        <span className="text-xs text-muted-foreground">
          {message.timestamp ? formatDistanceToNow(parseISO(message.timestamp), { addSuffix: true }) : 'Sending...'}
        </span>
        {isOutgoing && message.status && (
          <span className={isLast ? 'opacity-100' : 'opacity-0'}>
            {statusIcons[message.status] || null}
          </span>
        )}
      </div>
    </div>
  );
};

const ContactListItem = React.memo(({ contact, isSelected, onSelect, hasUnread }) => (
  <div onClick={() => onSelect(contact)} className={`p-3 cursor-pointer transition-colors ${
    isSelected ? 'bg-accent border-l-4 border-primary' : 'hover:bg-muted/50'
  }`}>
    <div className="flex items-center gap-3">
      <div className="relative">
        <Avatar className="h-10 w-10">
          <AvatarImage src={`https://ui-avatars.com/api/?name=${encodeURIComponent(contact.name || contact.whatsapp_id)}&background=random`} />
          <AvatarFallback>{contact.name?.substring(0, 2) || 'CN'}</AvatarFallback>
        </Avatar>
        {hasUnread && <div className="absolute -top-1 -right-1 h-3 w-3 rounded-full bg-primary border-2 border-background" />}
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 min-w-0">
            <p className="font-medium truncate">{contact.name || contact.whatsapp_id}</p>
            {contact.needs_human_intervention && <FiAlertCircle title="Needs Human Intervention" className="h-4 w-4 text-red-500 shrink-0" />}
          </div>
          {contact.last_message_date ? (
            <span className="text-[10px] text-muted-foreground whitespace-nowrap ml-2">
              {formatDistanceToNow(parseISO(contact.last_message_date), { addSuffix: true })}
            </span>
          ) : (
            <FiChevronRight className="h-4 w-4 text-muted-foreground" />
          )}
        </div>
        <p className="text-xs text-muted-foreground truncate">{contact.last_message_preview || 'No messages yet'}</p>
      </div>
    </div>
  </div>
));

export default function ConversationsPage() {
  const [contacts, setContacts] = useState([]);
  const [selectedContact, setSelectedContact] = useAtom(selectedContactAtom);
  const [messages, setMessages] = useState([]);
  const [newMessage, setNewMessage] = useState('');
  const [isLoading, setIsLoading] = useState({ contacts: true, messages: false });
  const [searchTerm, setSearchTerm] = useState('');
  const [debouncedSearchTerm] = useDebounce(searchTerm, 300);
  const [hasMoreMessages, setHasMoreMessages] = useState(false);
  const [isLoadingMore, setIsLoadingMore] = useState(false);
  const messagesEndRef = useRef(null);
  const messagesContainerRef = useRef(null);
  const inputRef = useRef(null);
  const { accessToken } = useAuth();

  const getSocketUrl = useCallback(() => {
    if (accessToken && selectedContact?.id) {
      return `${API_BASE_URL.replace(/^http/, 'ws')}/ws/conversations/${selectedContact.id}/?token=${accessToken}`;
    }
    return null;
  }, [accessToken, selectedContact]);

  const { sendJsonMessage, lastJsonMessage, readyState } = useWebSocket(getSocketUrl, {
    shouldReconnect: () => true,
  });

  const fetchContacts = useCallback(async (search = '', silent = false) => {
    if (!silent) setIsLoading(prev => ({ ...prev, contacts: true }));
    try {
      const response = await contactsApi.list({ search });
      const data = response.data;
      setContacts(data.results || data || []);
    } catch (error) {
      if (!silent) toast.error("Couldn't load contacts");
    } finally {
      if (!silent) setIsLoading(prev => ({ ...prev, contacts: false }));
    }
  }, []);

  const fetchMessages = useCallback(async (contactId, beforeId = null) => {
    if (!contactId) return;
    if (beforeId) {
      setIsLoadingMore(true);
    } else {
      setIsLoading(prev => ({ ...prev, messages: true }));
    }
    try {
      const params = { limit: 50 };
      if (beforeId) params.before = beforeId;
      const response = await contactsApi.listMessages(contactId, params);
      const data = response.data;
      const results = (data.results || data || []).reverse();
      setHasMoreMessages(!!data.has_more);
      if (beforeId) {
        setMessages(prev => [...results, ...prev]);
      } else {
        setMessages(results);
      }
    } catch (error) {
      toast.error("Couldn't load messages");
    } finally {
      if (beforeId) {
        setIsLoadingMore(false);
      } else {
        setIsLoading(prev => ({ ...prev, messages: false }));
      }
    }
  }, []);

  const loadOlderMessages = useCallback(() => {
    if (!selectedContact || !hasMoreMessages || isLoadingMore) return;
    const oldestMsg = messages[0];
    if (oldestMsg) {
      fetchMessages(selectedContact.id, oldestMsg.id);
    }
  }, [selectedContact, hasMoreMessages, isLoadingMore, messages, fetchMessages]);

  useEffect(() => { fetchContacts(debouncedSearchTerm); }, [debouncedSearchTerm, fetchContacts]);

  // Poll contacts every 10s so the list reorders when other contacts receive messages
  useEffect(() => {
    const interval = setInterval(() => {
      fetchContacts(debouncedSearchTerm, true);
    }, 10000);
    return () => clearInterval(interval);
  }, [debouncedSearchTerm, fetchContacts]);

  useEffect(() => {
    if (selectedContact) {
      setMessages([]);
      setHasMoreMessages(false);
      fetchMessages(selectedContact.id);
      inputRef.current?.focus();
    } else {
      setMessages([]);
      setHasMoreMessages(false);
    }
  }, [selectedContact, fetchMessages]);

  useEffect(() => {
    if (!lastJsonMessage) return;
    const { type, message, contact: updatedContactData } = lastJsonMessage;
    if (type === 'new_message' && message) {
      // Append or update the message in the current chat
      if (selectedContact && message.contact === selectedContact.id) {
        setMessages(prev => {
          const idx = prev.findIndex(msg => msg.id === message.id);
          if (idx !== -1) { const updated = [...prev]; updated[idx] = message; return updated; }
          return [...prev, message];
        });
      }
      // Update the contact's last_message_date and preview so sorting stays correct
      setContacts(prev => prev.map(c => {
        if (c.id === message.contact) {
          return { ...c, last_message_date: message.timestamp, last_message_preview: message.text_content || message.content_preview || c.last_message_preview };
        }
        return c;
      }));
    } else if (type === 'contact_updated' && updatedContactData) {
      setContacts(prev => prev.map(c => c.id === updatedContactData.id ? { ...c, ...updatedContactData } : c));
      if (selectedContact?.id === updatedContactData.id) {
        setSelectedContact(updatedContactData);
      }
    }
  }, [lastJsonMessage, selectedContact, setSelectedContact]);

  // Auto-scroll to bottom only when new messages arrive at the end (not when loading older)
  const prevMsgCountRef = useRef(0);
  useEffect(() => {
    const prevCount = prevMsgCountRef.current;
    prevMsgCountRef.current = messages.length;
    // Scroll to bottom on initial load or when a new message is appended
    if (prevCount === 0 || messages.length - prevCount <= 2) {
      messagesEndRef.current?.scrollIntoView({ behavior: prevCount === 0 ? 'instant' : 'smooth' });
    }
  }, [messages]);

  const handleSendMessage = async (e) => {
    e.preventDefault();
    if (!newMessage.trim() || !selectedContact) return;
    const msgText = newMessage.trim();
    // Immediately bump the contact to the top of the list
    const now = new Date().toISOString();
    setContacts(prev => prev.map(c =>
      c.id === selectedContact.id
        ? { ...c, last_message_date: now, last_message_preview: msgText }
        : c
    ));
    if (readyState === ReadyState.OPEN) {
      sendJsonMessage({ type: 'send_message', message: msgText });
      setNewMessage('');
    } else {
      // REST API fallback when WebSocket is not connected
      try {
        const res = await contactsApi.sendMessage(selectedContact.id, msgText);
        setMessages(prev => [...prev, res.data]);
        setNewMessage('');
      } catch {
        toast.error("Cannot send message. Connection is not live.");
      }
    }
  };

  const handleToggleIntervention = () => {
    if (!selectedContact || readyState !== ReadyState.OPEN) {
      toast.error("Cannot update status. Connection is not live.");
      return;
    }
    sendJsonMessage({ type: 'toggle_intervention' });
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSendMessage(e); }
  };

  const connectionStatus = {
    [ReadyState.CONNECTING]: { text: 'Connecting...', color: 'text-yellow-500', bgColor: 'bg-yellow-500' },
    [ReadyState.OPEN]: { text: 'Live', color: 'text-green-500', bgColor: 'bg-green-500' },
    [ReadyState.CLOSING]: { text: 'Closing...', color: 'text-orange-500', bgColor: 'bg-orange-500' },
    [ReadyState.CLOSED]: { text: 'Disconnected', color: 'text-red-500', bgColor: 'bg-red-500' },
    [ReadyState.UNINSTANTIATED]: { text: 'Offline', color: 'text-gray-500', bgColor: 'bg-gray-500' },
  }[readyState];

  // Sort contacts by latest message date (most recent first)
  const sortedContacts = useMemo(() => {
    return [...contacts].sort((a, b) => {
      const dateA = a.last_message_date ? new Date(a.last_message_date) : new Date(0);
      const dateB = b.last_message_date ? new Date(b.last_message_date) : new Date(0);
      return dateB - dateA;
    });
  }, [contacts]);

  return (
    <div className="flex h-0 flex-1 min-h-0 overflow-hidden rounded-xl border bg-background shadow-sm">
      {/* Contacts Panel */}
      <div className={`${selectedContact ? 'hidden md:flex md:w-96' : 'flex w-full'} border-r flex-col bg-background transition-all duration-300 h-full`}>
        <div className="p-3 border-b shrink-0 bg-background z-10">
          <div className="relative">
            <FiSearch className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input placeholder="Search contacts..." className="pl-9" value={searchTerm} onChange={(e) => setSearchTerm(e.target.value)} />
          </div>
        </div>
        <div className="flex-1 min-h-0 overflow-y-auto">
          {isLoading.contacts ? (
            <div className="space-y-2 p-4">{[...Array(5)].map((_, i) => (
              <div key={i} className="flex items-center gap-3 p-3">
                <div className="h-10 w-10 rounded-full bg-muted animate-pulse" />
                <div className="flex-1 space-y-2"><div className="h-4 w-3/4 bg-muted rounded animate-pulse" /><div className="h-3 w-1/2 bg-muted rounded animate-pulse" /></div>
              </div>
            ))}</div>
          ) : sortedContacts.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full p-6 text-center">
              <FiUsers className="h-12 w-12 mb-4 text-muted-foreground/30" />
              <p className="text-muted-foreground">No contacts found</p>
              <p className="text-sm text-muted-foreground/70 mt-1">{searchTerm ? 'Try a different search' : 'Contacts will appear once messages are received'}</p>
            </div>
          ) : (
            sortedContacts.map(contact => (
              <ContactListItem key={contact.id} contact={contact} isSelected={selectedContact?.id === contact.id} onSelect={setSelectedContact} hasUnread={contact.unread_count > 0} />
            ))
          )}
        </div>
      </div>

      {/* Messages Panel */}
      {selectedContact ? (
        <div className="flex-1 flex flex-col bg-background h-full min-h-0">
          <div className="p-3 border-b flex items-center justify-between shrink-0 bg-background z-10">
            <div className="flex items-center gap-3">
              <Button variant="ghost" size="icon" onClick={() => { setSelectedContact(null); fetchContacts(debouncedSearchTerm); }} className="md:hidden"><FiArrowLeft className="h-5 w-5" /></Button>
              <Avatar>
                <AvatarImage src={`https://ui-avatars.com/api/?name=${encodeURIComponent(selectedContact.name || selectedContact.whatsapp_id)}`} />
                <AvatarFallback>{selectedContact.name?.substring(0, 2) || 'CN'}</AvatarFallback>
              </Avatar>
              <div>
                <h2 className="font-semibold">{selectedContact.name || selectedContact.whatsapp_id}</h2>
                <div className="flex items-center gap-2">
                  <p className="text-xs text-muted-foreground">
                    {selectedContact.last_seen ? `Active ${formatDistanceToNow(parseISO(selectedContact.last_seen), { addSuffix: true })}` : 'Offline'}
                  </p>
                  <div className="flex items-center gap-1.5">
                    <span className={`h-1.5 w-1.5 rounded-full ${connectionStatus.bgColor}`}></span>
                    <span className={`text-xs ${connectionStatus.color}`}>{connectionStatus.text}</span>
                  </div>
                </div>
              </div>
            </div>
            <div className="flex items-center gap-1">
              <TooltipProvider delayDuration={100}>
                {selectedContact.phone_number && (
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <Button variant="ghost" size="icon" asChild>
                        <a href={`tel:${selectedContact.phone_number}`} aria-label="Call">
                          <FiPhone className="h-5 w-5 text-green-600" />
                        </a>
                      </Button>
                    </TooltipTrigger>
                    <TooltipContent side="bottom">Call</TooltipContent>
                  </Tooltip>
                )}
                {(selectedContact.whatsapp_id || selectedContact.phone_number) && (
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <Button variant="ghost" size="icon" asChild>
                        <a
                          href={`https://wa.me/${(selectedContact.whatsapp_id || selectedContact.phone_number || '').replace(/\D/g, '')}`}
                          target="_blank"
                          rel="noopener noreferrer"
                          aria-label="Open in WhatsApp"
                        >
                          <BsWhatsapp className="h-5 w-5 text-green-500" />
                        </a>
                      </Button>
                    </TooltipTrigger>
                    <TooltipContent side="bottom">Open in WhatsApp</TooltipContent>
                  </Tooltip>
                )}
              </TooltipProvider>
              <DropdownMenu>
                <DropdownMenuTrigger asChild><Button variant="ghost" size="icon"><FiMoreVertical className="h-5 w-5" /></Button></DropdownMenuTrigger>
                <DropdownMenuContent align="end">
                  <DropdownMenuItem onClick={() => toast.info('Contact profile is shown on the Contacts page.', { action: { label: 'Open', onClick: () => window.location.href = `/contacts?id=${selectedContact.id}` } })}>View profile</DropdownMenuItem>
                  <DropdownMenuItem onClick={() => toast.info('Mark as unread coming soon.')}>Mark as unread</DropdownMenuItem>
                  <DropdownMenuItem className="text-destructive" onClick={() => toast.warning('Chat deletion is not yet supported.')}>Delete chat</DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </div>
          </div>

          {selectedContact.needs_human_intervention && (
            <div className="bg-yellow-100 dark:bg-yellow-900/30 border-b border-yellow-300 dark:border-yellow-700 p-2 flex items-center justify-between gap-4 text-sm shrink-0">
              <div className="flex items-center gap-2">
                <FiAlertCircle className="h-5 w-5 text-yellow-600 dark:text-yellow-400 flex-shrink-0" />
                <p className="font-medium text-yellow-800 dark:text-yellow-200">Automated responses are paused.</p>
              </div>
              <Button variant="outline" size="sm" onClick={handleToggleIntervention}>Re-enable Bot</Button>
            </div>
          )}

          <div className="flex-1 min-h-0 overflow-y-auto" ref={messagesContainerRef}>
            {isLoading.messages ? (
              <div className="flex justify-center items-center h-full"><FiLoader className="animate-spin h-6 w-6 text-muted-foreground" /></div>
            ) : messages.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-full text-muted-foreground">
                <FiMessageSquare className="h-12 w-12 mb-4 opacity-30" />
                <h3 className="text-lg font-medium">No messages yet</h3>
                <p className="text-sm mt-1">Send your first message to {selectedContact.name || 'this contact'}</p>
              </div>
            ) : (
              <div className="p-4 space-y-3">
                {hasMoreMessages && (
                  <div className="flex justify-center py-2">
                    <Button variant="ghost" size="sm" onClick={loadOlderMessages} disabled={isLoadingMore} className="text-xs text-muted-foreground">
                      {isLoadingMore ? <><FiLoader className="animate-spin h-3 w-3 mr-2" />Loading...</> : 'Load older messages'}
                    </Button>
                  </div>
                )}
                {messages.map((msg, i) => (<MessageBubble key={msg.id} message={msg} isLast={i === messages.length - 1} />))}
                <div ref={messagesEndRef} />
              </div>
            )}
          </div>

          <div className="p-3 border-t bg-background shrink-0">
            <form onSubmit={handleSendMessage} className="flex items-end gap-2">
              <Button type="button" variant="ghost" size="icon" className="text-muted-foreground" onClick={() => toast.info('File attachments coming soon.')}><FiPaperclip className="h-5 w-5" /></Button>
              <Textarea ref={inputRef} value={newMessage} onChange={(e) => setNewMessage(e.target.value)} onKeyDown={handleKeyDown} placeholder="Type a message..." rows={1} className="flex-1 py-3 min-h-[44px] max-h-[120px] overflow-y-auto resize-none" />
              <Button type="submit" size="sm" disabled={!newMessage.trim()} className="h-[44px]"><FiSend className="h-4 w-4" /></Button>
            </form>
          </div>
        </div>
      ) : (
        <div className="hidden md:flex flex-1 flex-col items-center justify-center p-10 text-center text-muted-foreground">
          <FiMessageSquare className="h-24 w-24 mb-4 opacity-20" />
          <h3 className="text-xl font-medium mb-2">Select a conversation</h3>
          <p className="max-w-md text-sm">Choose from your existing conversations or start a new one</p>
        </div>
      )}
    </div>
  );
}
