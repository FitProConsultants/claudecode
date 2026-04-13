import {Composition} from 'remotion';
import {MyComposition} from './Composition';

// Each <Composition> is an individual video that can be rendered.
// Add markup to the Composition component to define the default values of the composition.
// See: https://www.remotion.dev/docs/composition

export const RemotionRoot: React.FC = () => {
	return (
		<>
			<Composition
				// You can take the "id" to determine what to render in "src/Composition.tsx"
				id="MyComp"
				component={MyComposition}
				durationInFrames={60}
				fps={30}
				width={1280}
				height={720}
			/>
		</>
	);
};
