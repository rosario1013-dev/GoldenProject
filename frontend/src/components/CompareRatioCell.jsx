import { Tag } from 'antd';

import { comparePosition, formatCompareValue } from '../utils/compareRatios';

export default function CompareRatioCell({ value, benchmark, percent = false }) {
  const position = comparePosition(value, benchmark);
  const display = formatCompareValue(value, { percent });

  return (
    <div className="compare-ratio-cell">
      {position === 'ahead' ? (
        <Tag bordered={false} className="compare-ratio-cell__tag compare-ratio-cell__tag--ahead">
          超前
        </Tag>
      ) : (
        <span className="compare-ratio-cell__tag compare-ratio-cell__tag--placeholder" />
      )}
      <div className="compare-ratio-cell__value">{display}</div>
      {position === 'behind' ? (
        <Tag bordered={false} className="compare-ratio-cell__tag compare-ratio-cell__tag--behind">
          落后
        </Tag>
      ) : (
        <span className="compare-ratio-cell__tag compare-ratio-cell__tag--placeholder" />
      )}
    </div>
  );
}
