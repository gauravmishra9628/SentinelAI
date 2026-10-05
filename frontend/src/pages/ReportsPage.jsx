const reports = [
  { title: 'Daily safety summary', time: '08:00' },
  { title: 'Traffic anomaly report', time: 'Yesterday' },
  { title: 'Patrol effectiveness', time: 'This week' },
];

const ReportsPage = () => (
  <div className="page-content">
    <div className="panel-card">
      <h3>Reports</h3>
      <ul className="alert-list">
        {reports.map((report) => (
          <li key={report.title} className="alert-row">
            <div>
              <strong>{report.title}</strong>
            </div>
            <span className="badge neutral">{report.time}</span>
          </li>
        ))}
      </ul>
    </div>
  </div>
);

export default ReportsPage;
