const events = [
  { id: 1, title: 'Wrong-way vehicle', score: 91, camera: 'CAM-014', region: 'Airport Road Junction' },
  { id: 2, title: 'Overspeeding cluster', score: 78, camera: 'CAM-008', region: 'NH-24 Highway' },
  { id: 3, title: 'Pedestrian near fast lane', score: 62, camera: 'CAM-022', region: 'School Zone' },
];

const RiskDetectionPage = () => (
  <div className="page-content">
    <div className="panel-card">
      <h3>AI risk detection</h3>
      <div className="risk-list">
        {events.map((event) => (
          <div key={event.id} className="risk-item">
            <div>
              <strong>{event.title}</strong>
              <small>{event.camera} • {event.region}</small>
            </div>
            <span className="risk-score">{event.score}</span>
          </div>
        ))}
      </div>
    </div>
  </div>
);

export default RiskDetectionPage;
