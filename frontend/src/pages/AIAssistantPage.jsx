const assistantTasks = [
  'Summarize threats around Airport Road Junction.',
  'Check whether the current vehicle pattern matches a known risk profile.',
  'Recommend a patrol assignment for the next 30 minutes.',
];

const AIAssistantPage = () => (
  <div className="page-content">
    <div className="panel-card">
      <h3>AI assistant</h3>
      <ul className="stack-list">
        {assistantTasks.map((task) => (
          <li key={task}><strong>{task}</strong></li>
        ))}
      </ul>
    </div>
  </div>
);

export default AIAssistantPage;
