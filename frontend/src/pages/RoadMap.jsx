const hotspots = [
  'Main Highway • Sector 7',
  'Airport Road Junction',
  'Downtown School Zone',
  'Ring Road Exit 11',
];

const RoadMap = () => (
  <div className="page-content">
    <div className="panel-card">
      <h3>Road map</h3>
      <div className="map-layout">
        <div className="map-lines" aria-hidden="true" />
        <div className="map-pins">
          {hotspots.map((item, index) => (
            <div key={item} className="map-pin" style={{ top: `${18 + index * 18}%`, left: `${22 + (index % 2) * 28}%` }}>
              {item}
            </div>
          ))}
        </div>
      </div>
    </div>
  </div>
);

export default RoadMap;
