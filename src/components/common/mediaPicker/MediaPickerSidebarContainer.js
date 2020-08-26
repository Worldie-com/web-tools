import PropTypes from 'prop-types';
import React from 'react';
import { injectIntl } from 'react-intl';
import { connect } from 'react-redux';
import { initializePreviouslySelectedMedia, clearSelectedMedia, resetMetadataShortlist } from '../../../actions/systemActions';

function composeMediaPickerSidebarContainer() {
  return (ChildComponent) => {
    class MediaPickerSidebarContainer extends React.Component {
      componentDidUpdate(prevProps) {
        // compare and select incoming media
        const { initMedia } = this.props;
        if (JSON.stringify(initMedia) !== JSON.stringify(prevProps.initMedia)) {
          if (initMedia) { // expects an array of media from caller
            this.props.handleInitialSelectionOfMedia(initMedia);
          }
        }
      }

      componentWillUnmount() {
        const { reset } = this.props;
        reset();
      }

      render() {
        const { selectedMedia, onConfirmSelection } = this.props;
        let content = null;
        content = (
          <div>
            <div className="select-media-dialog-inner">
              <ChildComponent {...this.props} selectedMedia={selectedMedia} onConfirmSelection={onConfirmSelection} />;
            </div>
          </div>
        );

        return content;
      }
    }

    MediaPickerSidebarContainer.propTypes = {
      // from context
      intl: PropTypes.object.isRequired,
      // from parent/implementer
      initMedia: PropTypes.array,
      handleInitialSelectionOfMedia: PropTypes.func.isRequired,
      reset: PropTypes.func.isRequired,
      setQueryFormChildDialogOpen: PropTypes.func,
      onConfirmSelection: PropTypes.func,
      // from state
      selectedMedia: PropTypes.array,
    };

    const mapStateToProps = state => ({
      selectedMedia: state.system.mediaPicker.selectMedia.list, // initially empty
    });

    const mapDispatchToProps = dispatch => ({
      reset: () => {
        dispatch(clearSelectedMedia());
        dispatch(resetMetadataShortlist());
      },
      handleInitialSelectionOfMedia: (prevSelectedMedia) => {
        if (prevSelectedMedia) {
          dispatch(initializePreviouslySelectedMedia(prevSelectedMedia)); // disable button too
        }
      },
    });

    return injectIntl(
      connect(mapStateToProps, mapDispatchToProps)(
        MediaPickerSidebarContainer
      )
    );
  };
}

export default composeMediaPickerSidebarContainer;
