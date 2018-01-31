import PropTypes from 'prop-types';
import React from 'react';
import { FormattedMessage, injectIntl } from 'react-intl';
import { connect } from 'react-redux';
import composeAsyncContainer from '../../../../../common/AsyncContainer';
import { fetchCreateFocusMediaTypeCoverage } from '../../../../../../actions/topicActions';
import DataCard from '../../../../../common/DataCard';
import PieChart from '../../../../../vis/PieChart';
import { getBrandDarkColor } from '../../../../../../styles/colors';

const localMessages = {
  title: { id: 'topic.snapshot.mediaType.coverage.title', defaultMessage: 'Story Coverage' },
  intro: { id: 'topic.snapshot.mediaType.coverage.intro', defaultMessage: 'By Media Type' },
  included: { id: 'topic.snapshot.mediaType.coverage.matching', defaultMessage: 'Stories about these media types for this topic' },
  notIncluded: { id: 'topic.snapshot.mediaType.coverage.total', defaultMessage: 'All Stories about this topic' },
};

class MediaTypeCoveragePreviewContainer extends React.Component {
  componentWillReceiveProps(nextProps) {
    const { topicId, mediaTypeSelected, fetchData } = this.props;
    if (nextProps.mediaTypeSelected !== mediaTypeSelected) {
      fetchData(topicId, nextProps.mediaTypeSelected);
    }
  }
  render() {
    const { count, total } = this.props;
    const { formatMessage } = this.props.intl;
    let content = null;
    if (count !== null) {
      content = (
        <PieChart
          title={formatMessage(localMessages.title)}
          data={[
            { name: formatMessage(localMessages.included), y: count, color: getBrandDarkColor() },
            { name: formatMessage(localMessages.notIncluded), y: total, color: '#cccccc' },
          ]}
          height={250}
          showDataLabels={false}
        />
      );
    }
    return (
      <DataCard>
        <h2>
          <FormattedMessage {...localMessages.title} />
        </h2>
        <p><FormattedMessage {...localMessages.intro} /></p>
        {content}
      </DataCard>
    );
  }
}

MediaTypeCoveragePreviewContainer.propTypes = {
  // from compositional chain
  intl: PropTypes.object.isRequired,
  // from parent
  topicId: PropTypes.number.isRequired,
  mediaTypeSelected: PropTypes.number.isRequired,
  // from dispatch
  asyncFetch: PropTypes.func.isRequired,
  fetchData: PropTypes.func.isRequired,
  // from state
  count: PropTypes.number,
  total: PropTypes.number,
  fetchStatus: PropTypes.string.isRequired,
};

const mapStateToProps = state => ({
  fetchStatus: state.topics.selected.focalSets.create.mediaTypeCoverage.fetchStatus,
  count: state.topics.selected.focalSets.create.mediaTypeCoverage.counts.count,
  total: state.topics.selected.focalSets.create.mediaTypeCoverage.counts.total,
});

const mapDispatchToProps = dispatch => ({
  fetchData: (topicId, mediaTypeSelected) => {
    dispatch(fetchCreateFocusMediaTypeCoverage(topicId, { mediaTypeSelected }));
  },
});

function mergeProps(stateProps, dispatchProps, ownProps) {
  return Object.assign({}, stateProps, dispatchProps, ownProps, {
    asyncFetch: () => {
      dispatchProps.fetchData(ownProps.topicId, ownProps.mediaTypeSelected);
    },

  });
}

export default
  injectIntl(
    connect(mapStateToProps, mapDispatchToProps, mergeProps)(
      composeAsyncContainer(
        MediaTypeCoveragePreviewContainer
      )
    )
  );
