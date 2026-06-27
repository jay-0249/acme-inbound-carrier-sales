import './Skeleton.css'

function SkeletonBox({ h, w }) {
  return <div className="skel" style={{ height: h, width: w ?? '100%' }} />
}

export default function Skeleton() {
  return (
    <div className="skeleton-wrap" aria-busy="true" aria-label="Loading dashboard">
      <div className="skel-hero">
        {[0,1,2,3].map(i => (
          <div key={i} className="skel-card">
            <SkeletonBox h="12px" w="60%" />
            <SkeletonBox h="52px" w="70%" />
            <SkeletonBox h="12px" w="80%" />
          </div>
        ))}
      </div>
      <div className="skel-row">
        <div className="skel-card skel-wide">
          <SkeletonBox h="12px" w="40%" />
          {[0,1,2,3,4,5].map(i => <SkeletonBox key={i} h="24px" />)}
        </div>
        <div className="skel-card skel-wider">
          <SkeletonBox h="12px" w="40%" />
          {[0,1,2].map(i => <SkeletonBox key={i} h="40px" />)}
        </div>
      </div>
    </div>
  )
}
