import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { HistoryView } from '../components/HistoryView';
import { endpoints } from '../config';

interface HistoryPageProps {
  onSelectSession: (id: string) => void;
}

export const HistoryPage: React.FC<HistoryPageProps> = ({ onSelectSession }) => {
  const queryClient = useQueryClient();

  const { data: history = [], isLoading } = useQuery({
    queryKey: ['history'],
    queryFn: async () => {
      const response = await fetch(endpoints.history);
      if (!response.ok) throw new Error('Failed to fetch history');
      return response.json();
    },
  });

  const renameMutation = useMutation({
    mutationFn: async ({ id, title }: { id: string; title: string }) => {
      const response = await fetch(endpoints.transcriptionTitle(id), {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title }),
      });
      if (!response.ok) throw new Error('Failed to update title');
      return response.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['history'] });
    },
  });

  const handleRename = async (id: string, title: string) => {
    await renameMutation.mutateAsync({ id, title });
  };

  return (
    <div className="min-h-screen">
      <HistoryView
        history={history}
        isLoading={isLoading}
        onSelectItem={onSelectSession}
        onRename={handleRename}
      />
    </div>
  );
};
