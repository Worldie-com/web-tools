import React from 'react';
import { connect } from 'react-redux';

import ErrorTryAgain from '../../util/ErrorTryAgain';
import LoadingSpinner from '../../util/LoadingSpinner';
import SnapshotSelector from './SnapshotSelector';
import { fetchControversySnapshotsList, filterBySnapshot } from '../../../actions/controversyActions';
import * as fetchConstants from '../../../lib/fetchConstants.js';

class SnapshotSelectorContainer extends React.Component {
  componentDidMount() {
    const { fetchData, topicId } = this.props;
    fetchData(topicId);
  }
  getStyles() {
    const styles = {
      root: {
      },
    };
    return styles;
  }
  render() {
    const { snapshots, fetchStatus, fetchData, onSnapshotSelected } = this.props;
    let content = fetchStatus;
    const styles = this.getStyles();
    switch (fetchStatus) {
      case fetchConstants.FETCH_SUCCEEDED:
        content = <SnapshotSelector snapshots={snapshots} onSnapshotSelected={onSnapshotSelected} />;
        break;
      case fetchConstants.FETCH_FAILED:
        content = <ErrorTryAgain onTryAgain={fetchData} />;
        break;
      default:
        content = <LoadingSpinner />;
    }
    return (
      <div style={styles.root}>
        {content}
      </div>
    );
  }
}

SnapshotSelectorContainer.propTypes = {
  fetchStatus: React.PropTypes.string.isRequired,
  snapshots: React.PropTypes.array.isRequired,
  fetchData: React.PropTypes.func.isRequired,
  onSnapshotSelected: React.PropTypes.func.isRequired,
  topicId: React.PropTypes.number.isRequired,
};

const mapStateToProps = (state) => ({
  topicId: state.controversies.selected.id,
  fetchStatus: state.controversies.selected.snapshots.fetchStatus,
  snapshots: state.controversies.selected.snapshots.list,
});

const mapDispatchToProps = (dispatch) => ({
  fetchData: (topicId) => {
    dispatch(fetchControversySnapshotsList(topicId));
  },
  onSnapshotSelected: (event) => {
    dispatch(filterBySnapshot(event.target.value));
  },
});

export default connect(
  mapStateToProps,
  mapDispatchToProps
)(SnapshotSelectorContainer);
